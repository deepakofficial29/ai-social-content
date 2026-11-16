"""Local filesystem storage implementation.

Files are stored under STORAGE_DIR/<storage_key>.
The storage directory is intentionally outside any web-served directory.
"""

import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger
from app.core.security import safe_join
from app.storage.base import BaseStorage

logger = get_logger(__name__)


class LocalStorage(BaseStorage):
    def __init__(self, base_dir: str | None = None):
        settings = get_settings()
        self._base = Path(base_dir or settings.STORAGE_DIR).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def generate_key(self, extension: str) -> str:
        """Return a unique storage key with the given file extension."""
        return f"{uuid.uuid4().hex}{extension}"

    # ------------------------------------------------------------------
    def save(self, data: bytes, storage_key: str) -> str:
        dest = self._resolve(storage_key)
        if dest.exists():
            raise StorageError(f"Storage key already exists: {storage_key}")
        tmp = dest.with_suffix(".tmp")
        try:
            tmp.write_bytes(data)
            tmp.rename(dest)
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            raise StorageError(f"Failed to write {storage_key}: {exc}") from exc
        logger.debug("Saved %s (%d bytes)", storage_key, len(data))
        return storage_key

    def load(self, storage_key: str) -> bytes:
        path = self._resolve(storage_key)
        if not path.exists():
            raise StorageError(f"Storage key not found: {storage_key}")
        return path.read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.exists():
            path.unlink()
            logger.debug("Deleted %s", storage_key)

    def exists(self, storage_key: str) -> bool:
        return self._resolve(storage_key).exists()

    def get_size(self, storage_key: str) -> int:
        path = self._resolve(storage_key)
        if not path.exists():
            raise StorageError(f"Storage key not found: {storage_key}")
        return path.stat().st_size

    # ------------------------------------------------------------------
    def _resolve(self, storage_key: str) -> Path:
        return safe_join(self._base, storage_key)
