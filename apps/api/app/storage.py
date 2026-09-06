"""Converts a local-storage filesystem path (as stored on Video/Asset rows)
into a URL the frontend can fetch, via the /storage static mount registered
in main.py. Only meaningful for STORAGE_BACKEND=local; a future S3 backend
would return a signed URL here instead — callers go through this function
rather than reading final_video_path/path directly so that swap stays
contained to one place.
"""

from app.config import settings


def to_url(path: str | None) -> str | None:
    if not path:
        return None
    root = settings.local_storage_root.rstrip("/")
    if path.startswith(root):
        path = path[len(root) :]
    return f"/storage/{path.lstrip('/')}"
