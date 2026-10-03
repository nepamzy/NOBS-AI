"""YouTube connector — uploads finished videos, but ONLY ever as private.

Nobert's explicit instruction after reviewing an earlier, unsafe draft of
this connector: it must have a review step, same as every other connector
in this project (Gmail: drafts only, never sends; GitHub: PR only, never
merges; Vercel: never deploys). There is deliberately NO code path here
that makes a video public by itself — not on upload, not on a timer.
`upload_video()` always uploads as private. `publish_video()` is a
separate, explicit action that must be called on its own — wired up so it
only ever runs when Nobert (or the assistant, because he explicitly asked
in that exact conversation turn) decides to flip a specific video public,
after watching the finished result.

Auth: a Google OAuth refresh token (GOOGLE_YOUTUBE_REFRESH_TOKEN) from a
SEPARATE OAuth client than Gmail's (different scope — youtube.upload, not
gmail), exchanged for a short-lived access token on every call. Getting it
is a one-time Google Cloud Console setup Nobert has to do himself — see
YOUTUBE_SETUP.md.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from services.common.errors import EngineNotConfiguredError

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_REQUEST_TIMEOUT_SECONDS = 30
_UPLOAD_TIMEOUT_SECONDS = 300  # video files are much larger than a typical API call


@dataclass
class VideoUploadResult:
    video_id: str
    title: str
    privacy_status: str  # always "private" — see module docstring


class YouTubeConnector:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    def _require_configured(self) -> None:
        if not (self._client_id and self._client_secret and self._refresh_token):
            raise EngineNotConfiguredError(
                "No GOOGLE_YOUTUBE_CLIENT_ID/GOOGLE_YOUTUBE_CLIENT_SECRET/"
                "GOOGLE_YOUTUBE_REFRESH_TOKEN configured — YouTube upload "
                "needs a one-time OAuth setup in Google Cloud Console "
                "(YouTube Data API v3, its own OAuth client) before it can "
                "upload anything. See YOUTUBE_SETUP.md."
            )

    def _access_token(self) -> str:
        response = httpx.post(
            _TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
    ) -> VideoUploadResult:
        """Uploads as PRIVATE — always, no parameter to change that. Nobert
        reviews it in YouTube Studio (or asks the assistant to describe it)
        and calls publish_video() himself when he's ready to make it public."""
        self._require_configured()

        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        metadata = {
            "snippet": {"title": title[:100], "description": description, "tags": tags or []},
            "status": {"privacyStatus": "private"},
        }

        response = httpx.post(
            f"{_UPLOAD_URL}?part=snippet,status&uploadType=multipart",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            files={
                "metadata": (None, json.dumps(metadata), "application/json"),
                "file": (path.name, path.read_bytes(), "video/mp4"),
            },
            timeout=_UPLOAD_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()

        return VideoUploadResult(
            video_id=result["id"],
            title=result["snippet"]["title"],
            privacy_status=result["status"]["privacyStatus"],
        )

    def get_upload_status(self, video_id: str) -> dict:
        """Check processing/privacy status of a previously uploaded video."""
        self._require_configured()

        response = httpx.get(
            _VIDEOS_URL,
            params={"id": video_id, "part": "processingDetails,status"},
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            return {"status": "not_found"}

        video = items[0]
        return {
            "video_id": video_id,
            "processing_status": video.get("processingDetails", {}).get("processingStatus"),
            "privacy_status": video.get("status", {}).get("privacyStatus"),
            "upload_status": video.get("status", {}).get("uploadStatus"),
        }

    def publish_video(self, video_id: str) -> dict:
        """Makes a private video public. The ONLY place in this whole
        connector that does that — called only on an explicit, separate
        request, never automatically from the generation pipeline."""
        self._require_configured()

        response = httpx.put(
            _VIDEOS_URL,
            params={"part": "status"},
            headers={"Authorization": f"Bearer {self._access_token()}"},
            json={"id": video_id, "status": {"privacyStatus": "public"}},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
