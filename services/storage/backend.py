"""Storage abstraction. Default is local filesystem (free). Switching to S3
or another object store later is a paid-infra decision that needs a cost
warning + approval per CLAUDE.md Part 1 before it's wired in here.
"""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def save(self, local_source_path: str, relative_dest_path: str) -> str:
        """Store a local file, returning the path/key it's accessible at."""

    @abstractmethod
    def resolve(self, relative_path: str) -> str:
        """Return an absolute, readable path/URL for a stored file."""


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: str):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, local_source_path: str, relative_dest_path: str) -> str:
        dest = self._root / relative_dest_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_source_path, dest)
        return str(dest)

    def resolve(self, relative_path: str) -> str:
        return str(self._root / relative_path)


def build_storage_backend(backend_name: str, local_root: str) -> StorageBackend:
    if backend_name == "local":
        return LocalStorageBackend(local_root)
    raise NotImplementedError(
        f"Storage backend '{backend_name}' is not implemented — only 'local' "
        "is available until a paid storage option is chosen and approved."
    )
