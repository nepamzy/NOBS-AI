"""Files a video that was produced OUTSIDE NOBS AI (e.g. by a Claude session
that wrote the script, made the footage and recorded the voiceover) as a
finished project, so it shows up on the dashboard with every pipeline step
ticked and is ready for the normal review -> upload -> publish flow.

Nothing here spends money: no LLM, GPU or voice call is made — the files are
already made. It only downloads, probes, stores (through the same
StorageBackend every pipeline artifact uses) and writes rows.

What an import deliberately does NOT do: upload to YouTube or publish. The
imported video lands as COMPLETED and waits for Nobert, exactly like a
manually-reviewed pipeline video (CLAUDE.md: publishing is a deliberate,
separate human action).
"""

import ipaddress
import json
import logging
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.asset import Asset
from app.models.enums import AssetType, PipelineStage
from app.models.project import Project
from app.models.script import Scene, Script
from app.models.thumbnail import Thumbnail
from app.models.user import User
from app.models.video import Video
from services.rendering.ffmpeg.assembler import AssemblyError, extract_frame
from services.storage.backend import LocalStorageBackend, StorageBackend

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_NAME = "Imported from Claude"
MAX_SCENES = 60
_MAX_REDIRECTS = 3
_CONNECT_TIMEOUT_SECONDS = 15
_READ_TIMEOUT_SECONDS = 60

# Per-file-kind: (allowed suffixes, fallback suffix, max bytes). The video's
# own cap comes from settings (Supabase's free tier rejects files > 50 MB).
_AUDIO = ({".mp3", ".wav", ".m4a"}, ".mp3", 50 * 1024 * 1024)
_CAPTIONS = ({".srt", ".vtt"}, ".srt", 2 * 1024 * 1024)
_IMAGE = ({".jpg", ".jpeg", ".png"}, ".jpg", 10 * 1024 * 1024)


class ConnectorImportError(Exception):
    """A problem the caller can act on (bad URL, wrong file type, too big).
    The message is shown to the Claude session verbatim — keep it plain."""


@dataclass
class SceneInput:
    narration: str
    visual_prompt: str = ""
    duration_seconds: int = 0


@dataclass
class ImportRequest:
    title: str
    project_name: str = DEFAULT_PROJECT_NAME
    description: str = ""
    hook: str = ""
    scenes: list[SceneInput] = field(default_factory=list)
    # Local files, already downloaded/received and size-checked by the caller.
    video_path: Path | None = None
    voiceover_path: Path | None = None
    captions_path: Path | None = None
    thumbnail_path: Path | None = None


# --------------------------------------------------------------------------
# Safe downloading
# --------------------------------------------------------------------------


def _assert_public_https(url: str) -> None:
    """Refuses anything that isn't an https URL to a PUBLIC address. Without
    this, a connector caller could make our server fetch internal addresses
    (cloud metadata, localhost, the private network) on their behalf."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ConnectorImportError("URLs must be https:// links to a public file.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ConnectorImportError(f"Could not resolve {parsed.hostname}.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise ConnectorImportError(
                "That URL points at a non-public address, so it was refused."
            )


def _http_client() -> httpx.Client:
    # No automatic redirects: each hop is re-checked by _assert_public_https.
    return httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(_READ_TIMEOUT_SECONDS, connect=_CONNECT_TIMEOUT_SECONDS),
    )


def download_to_file(url: str, dest: Path, max_bytes: int) -> None:
    current = url
    with _http_client() as client:
        for _ in range(_MAX_REDIRECTS + 1):
            _assert_public_https(current)
            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise ConnectorImportError("The link redirected without a target.")
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise ConnectorImportError(
                            f"Download failed: the link returned HTTP {response.status_code}. "
                            "It must be a direct, publicly reachable file link."
                        )
                    declared = response.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > max_bytes:
                        raise ConnectorImportError(
                            f"File is {int(declared) // (1024 * 1024)} MB; the limit is "
                            f"{max_bytes // (1024 * 1024)} MB."
                        )
                    written = 0
                    with dest.open("wb") as handle:
                        for chunk in response.iter_bytes(1024 * 1024):
                            written += len(chunk)
                            if written > max_bytes:
                                raise ConnectorImportError(
                                    f"File is over the {max_bytes // (1024 * 1024)} MB limit."
                                )
                            handle.write(chunk)
                    return
            except httpx.HTTPError as exc:
                raise ConnectorImportError(f"Download failed: {type(exc).__name__}.") from exc
    raise ConnectorImportError("Too many redirects.")


def suffix_for(url: str, kind: tuple[set[str], str, int]) -> str:
    allowed, fallback, _ = kind
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in allowed else fallback


def fetch_optional(url: str, kind: tuple[set[str], str, int], work_dir: Path, stem: str) -> Path:
    path = work_dir / f"{stem}{suffix_for(url, kind)}"
    download_to_file(url, path, kind[2])
    return path


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def probe_video(path: Path) -> float:
    """Returns the duration in seconds, or raises if this isn't a playable
    video. Trusting the file extension alone would let anything through."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration,format_name:stream=codec_type",
                "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConnectorImportError("Could not inspect the video file.") from exc
    if result.returncode != 0:
        raise ConnectorImportError("That file isn't a readable video.")
    try:
        info = json.loads(result.stdout)
        has_video = any(s.get("codec_type") == "video" for s in info.get("streams", []))
        duration = float(info["format"]["duration"])
        format_name = str(info["format"].get("format_name", ""))
    except (ValueError, KeyError, TypeError) as exc:
        raise ConnectorImportError("That file isn't a readable video.") from exc
    if not has_video or duration <= 0:
        raise ConnectorImportError("That file has no video track.")
    # Stored and served as final.mp4, so anything else (webm, mkv...) might not play.
    if "mp4" not in format_name.split(","):
        raise ConnectorImportError("Only MP4 videos are supported — convert it to MP4 first.")
    return duration


# --------------------------------------------------------------------------
# Writing the project
# --------------------------------------------------------------------------


def _store(storage: StorageBackend, local: Path, key: str) -> str:
    """Persists one file and returns the path/URL to record. The local
    backend just hands the path back, but ours lives in a temp folder that is
    deleted right after the import — so for local storage the file is first
    copied under the storage root, like every pipeline artifact."""
    if isinstance(storage, LocalStorageBackend):
        target = Path(settings.local_storage_root) / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, target)
        return str(target)
    return storage.upload(str(local), key)


def _find_or_create_project(db: Session, user: User, name: str) -> Project:
    name = (name or DEFAULT_PROJECT_NAME).strip()[:255] or DEFAULT_PROJECT_NAME
    project = (
        db.query(Project).filter(Project.owner_id == user.id, Project.name == name).first()
    )
    if project is None:
        project = Project(owner_id=user.id, name=name)
        db.add(project)
        db.flush()
    return project


def import_finished_video(
    db: Session,
    user: User,
    request: ImportRequest,
    storage: StorageBackend,
    work_dir: Path,
) -> Video:
    """Creates a COMPLETED Video with its script, assets and thumbnails.
    Commits on success; on any failure nothing is left half-written."""
    if request.video_path is None:
        raise ConnectorImportError("No video file was provided.")
    if not request.title.strip():
        raise ConnectorImportError("A title is required.")
    if len(request.scenes) > MAX_SCENES:
        raise ConnectorImportError(f"At most {MAX_SCENES} scenes are supported.")

    duration = probe_video(request.video_path)
    duration_seconds = max(1, round(duration))

    try:
        project = _find_or_create_project(db, user, request.project_name)
        title = request.title.strip()

        video = Video(
            project_id=project.id,
            topic=title,
            target_duration_seconds=duration_seconds,
            voice_preset="external",
            style_preset="external",
            stage=PipelineStage.COMPLETED,
            stage_progress_percent=100,
            stage_detail="",
            storyboard_approved=True,
        )
        db.add(video)
        db.flush()

        _write_script(db, video, request, title, duration_seconds)

        video.final_video_path = _store(storage, request.video_path, f"{video.id}/final.mp4")
        db.add(
            Asset(
                video_id=video.id,
                asset_type=AssetType.FINAL_VIDEO,
                path=video.final_video_path,
                label="Final video",
            )
        )
        _store_extras(db, video, request, storage, work_dir, duration)

        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(video)
    return video


def _write_script(
    db: Session, video: Video, request: ImportRequest, title: str, duration_seconds: int
) -> None:
    scenes = request.scenes or [
        SceneInput(
            narration=request.description.strip() or title,
            duration_seconds=duration_seconds,
        )
    ]
    script = Script(
        video_id=video.id,
        title=title[:500],
        hook=(request.hook or request.description or title).strip(),
        estimated_duration_seconds=sum(s.duration_seconds for s in scenes) or duration_seconds,
        word_count=sum(len(s.narration.split()) for s in scenes),
        approved=True,
    )
    script.scenes = [
        Scene(
            order=i + 1,
            narration=s.narration.strip(),
            visual_prompt=s.visual_prompt.strip(),
            duration_seconds=max(1, s.duration_seconds),
        )
        for i, s in enumerate(scenes)
    ]
    db.add(script)


def _store_extras(
    db: Session,
    video: Video,
    request: ImportRequest,
    storage: StorageBackend,
    work_dir: Path,
    duration: float,
) -> None:
    if request.voiceover_path is not None:
        suffix = request.voiceover_path.suffix
        url = _store(storage, request.voiceover_path, f"{video.id}/voiceover{suffix}")
        db.add(
            Asset(
                video_id=video.id, asset_type=AssetType.VOICEOVER, path=url, label="Voiceover"
            )
        )

    if request.captions_path is not None:
        suffix = request.captions_path.suffix
        url = _store(storage, request.captions_path, f"{video.id}/captions{suffix}")
        db.add(Asset(video_id=video.id, asset_type=AssetType.CAPTIONS, path=url, label="Captions"))

    candidates: list[tuple[str, Path]] = []
    if request.thumbnail_path is not None:
        candidates.append(("A", request.thumbnail_path))
    else:
        # Same A/B/C frame grabs the normal pipeline makes (no image-gen cost).
        for label, fraction in (("A", 0.15), ("B", 0.5), ("C", 0.85)):
            frame = work_dir / f"thumbnail_{label}.jpg"
            try:
                extract_frame(str(request.video_path), round(duration * fraction, 2), str(frame))
            except (AssemblyError, OSError):
                logger.warning("Thumbnail %s extraction failed for imported video", label)
                continue
            if frame.exists():
                candidates.append((label, frame))

    for label, path in candidates:
        url = _store(storage, path, f"{video.id}/thumbnail_{label}{path.suffix}")
        db.add(Thumbnail(video_id=video.id, image_path=url, variant_label=label))
        db.add(
            Asset(
                video_id=video.id,
                asset_type=AssetType.THUMBNAIL,
                path=url,
                label=f"Thumbnail {label}",
            )
        )
