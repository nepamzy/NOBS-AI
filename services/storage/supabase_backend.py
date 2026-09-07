"""Uploads finished artifacts to a Supabase Storage bucket via its REST API
(httpx, not the full supabase-py SDK — this is the one thing it's used for).
Requires the bucket to already exist and be public (simplest way to get a
directly-fetchable URL back without also implementing signed-URL refresh).
"""

from pathlib import Path

import httpx

from services.common.errors import EngineNotConfiguredError
from services.storage.backend import StorageBackend

_UPLOAD_TIMEOUT_SECONDS = 60

_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".srt": "application/x-subrip",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


class SupabaseStorageBackend(StorageBackend):
    def __init__(self, project_url: str, service_role_key: str, bucket: str):
        self._project_url = project_url.rstrip("/")
        self._service_role_key = service_role_key
        self._bucket = bucket

    def upload(self, local_path: str, key: str) -> str:
        if not self._project_url or not self._service_role_key:
            raise EngineNotConfiguredError(
                "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not set — required "
                "to upload to Supabase Storage."
            )

        path = Path(local_path)
        content_type = _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")

        response = httpx.post(
            f"{self._project_url}/storage/v1/object/{self._bucket}/{key}",
            headers={
                "Authorization": f"Bearer {self._service_role_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            content=path.read_bytes(),
            timeout=_UPLOAD_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        return f"{self._project_url}/storage/v1/object/public/{self._bucket}/{key}"
