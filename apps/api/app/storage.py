"""Converts a stored path (as saved on Video/Asset rows) into a URL the
frontend can fetch. Once StorageBackend.upload() runs on an artifact (see
services/storage), what's stored is already an absolute Supabase Storage
URL — passed through unchanged. Only a plain local path (STORAGE_BACKEND=
local, or an artifact predating the upload step) gets the /storage/ static
mount prefix. Callers go through this function rather than reading
final_video_path/path directly so the local-vs-remote distinction stays
contained to one place.
"""

from app.config import settings


def to_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    root = settings.local_storage_root.rstrip("/")
    if path.startswith(root):
        path = path[len(root) :]
    return f"/storage/{path.lstrip('/')}"
