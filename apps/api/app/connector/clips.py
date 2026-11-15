"""Clips Claude cut itself: Claude finds the moments and cuts them in its own
sandbox, then hands each finished clip to NOBS AI over the connector. NOBS AI
files it under the Clips page (grouped by the source video's title) and
uploads it to YouTube.

Safety (same rules as everything else here): the upload is always PRIVATE.
Making a clip public happens only when `publish` is set, which the tool text
and server instructions reserve for when Nobert has explicitly said so. A clip
is stored and kept even if the YouTube step fails (not connected, rejected...),
so work is never lost and the failure is reported plainly.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app import publishing
from app.connector import importer
from app.connector.importer import ConnectorImportError
from app.models.clip import Clip
from app.models.enums import ClipJobStage
from app.models.source_video import SourceVideo
from app.models.user import User
from services.storage.backend import StorageBackend

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_TITLE = "Clips from Claude"
SOURCE_MARKER = "external:claude"


@dataclass
class ClipRequest:
    title: str
    video_path: Path
    description: str = ""
    source_title: str = DEFAULT_SOURCE_TITLE
    start_seconds: float | None = None
    end_seconds: float | None = None
    channel: str = "auto"
    publish: bool = False


def _find_or_create_source(db: Session, user: User, title: str) -> SourceVideo:
    name = (title or DEFAULT_SOURCE_TITLE).strip()[:500] or DEFAULT_SOURCE_TITLE
    source = (
        db.query(SourceVideo)
        .filter(
            SourceVideo.owner_id == user.id,
            SourceVideo.original_filename == name,
            SourceVideo.source_path == SOURCE_MARKER,
        )
        .first()
    )
    if source is None:
        source = SourceVideo(
            owner_id=user.id,
            original_filename=name,
            source_path=SOURCE_MARKER,
            stage=ClipJobStage.COMPLETED,
            stage_detail="",  # the Clips page shows any note here as a warning
            target_clip_count=0,
            auto_publish=False,  # Claude's clips are never auto-published by NOBS AI
        )
        db.add(source)
        db.flush()
    return source


def store_clip(
    db: Session,
    user: User,
    request: ClipRequest,
    storage: StorageBackend,
) -> Clip:
    """Validates and stores the clip file and records it. Does not touch YouTube."""
    if not request.title.strip():
        raise ConnectorImportError("A title is required.")
    duration = importer.probe_video(request.video_path)

    start = request.start_seconds if request.start_seconds is not None else 0.0
    end = request.end_seconds if request.end_seconds is not None else start + duration
    if start < 0 or end <= start:
        raise ConnectorImportError("end_seconds must be greater than start_seconds (both >= 0).")

    try:
        source = _find_or_create_source(db, user, request.source_title)
        clip = Clip(
            source_video_id=source.id,
            start_seconds=start,
            end_seconds=end,
            title=request.title.strip()[:200],
            reason=request.description.strip(),
        )
        db.add(clip)
        db.flush()
        clip.clip_path = importer._store(
            storage, request.video_path, f"clips/{source.id}/{clip.id}.mp4"
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(clip)
    return clip


def upload_stored_clip(
    db: Session, clip: Clip, channel: str, publish: bool
) -> tuple[Clip, str | None]:
    """The YouTube step. Returns (clip, error_message_or_None) — a failure here
    never discards the stored clip."""
    try:
        return publishing.upload_clip(db, clip, channel, publish), None
    except publishing.PublishingError as exc:
        db.refresh(clip)
        return clip, str(exc)


def clip_summary(clip: Clip, youtube_error: str | None = None) -> dict:
    from app.storage import to_url

    uploaded = bool(clip.youtube_video_id)
    return {
        "clip_id": str(clip.id),
        "title": clip.title,
        "source": clip.source_video.original_filename if clip.source_video else None,
        "clip_url": to_url(clip.clip_path),
        "youtube": {
            "uploaded": uploaded,
            "channel": clip.youtube_channel if uploaded else None,
            "video_id": clip.youtube_video_id,
            "url": f"https://youtu.be/{clip.youtube_video_id}" if uploaded else None,
            "published": clip.youtube_published,
        },
        "youtube_error": youtube_error,
    }
