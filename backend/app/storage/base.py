"""Abstract storage interface."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseStorage(ABC):
    @abstractmethod
    def save(self, data: bytes, storage_key: str) -> str:
        """Persist *data* under *storage_key*.  Returns the storage key."""

    @abstractmethod
    def load(self, storage_key: str) -> bytes:
        """Return the raw bytes stored under *storage_key*."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove the object identified by *storage_key*."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Return True if *storage_key* exists in the store."""

    @abstractmethod
    def get_size(self, storage_key: str) -> int:
        """Return the byte size of the stored object."""
