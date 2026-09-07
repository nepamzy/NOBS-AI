"""Persists a finished artifact (final video, thumbnail, captions) somewhere
that survives past the process that generated it. Render's local disk is
ephemeral — wiped on every redeploy/restart — so anything the user needs to
still be there afterward has to leave local disk, not just be written to it.

Intermediate/working files (per-scene clips, per-scene voiceovers) are
deliberately NOT uploaded — they're regenerable inputs, not the deliverable,
and re-running that stage recreates them. Only the outputs a person actually
looks at (the assembled video at each stage, thumbnails, the caption file)
go through this.
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def upload(self, local_path: str, key: str) -> str:
        """Uploads the file at local_path, returns a URL the frontend can
        fetch it from directly (already absolute — no /storage/ prefixing
        needed, unlike the local backend)."""


class LocalStorageBackend(StorageBackend):
    """Default. Free, but doesn't survive a redeploy on ephemeral disk — see
    module docstring. Returns the local path unchanged; app/storage.py's
    to_url() is what turns that into a fetchable /storage/... URL."""

    def upload(self, local_path: str, key: str) -> str:
        del key  # unused — local backend just keeps the file where it is
        return local_path
