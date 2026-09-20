import asyncio
import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings


class ImageNotFoundError(FileNotFoundError):
    pass


class ImageStorageService(ABC):
    """Storage contract used by the API independently of a storage provider."""

    @abstractmethod
    async def save(self, filename: str, content: bytes) -> None:
        """Persist image content under a server-generated filename."""

    @abstractmethod
    async def load(self, filename: str) -> bytes:
        """Return the original image content or raise ImageNotFoundError."""

    @abstractmethod
    async def delete(self, filename: str) -> None:
        """Remove an image. Deleting an absent file is intentionally idempotent."""


class LocalImageStorageService(ImageStorageService):
    """Local filesystem storage used by the current Docker deployment."""

    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path

    def _path_for(self, filename: str) -> Path:
        path = self._storage_path / filename
        if path.parent != self._storage_path:
            raise ValueError("Image filename must not contain a directory path")
        return path

    async def save(self, filename: str, content: bytes) -> None:
        destination = self._path_for(filename)
        temporary = destination.with_suffix(".uploading")

        def write_file() -> None:
            self._storage_path.mkdir(parents=True, exist_ok=True)
            try:
                temporary.write_bytes(content)
                os.replace(temporary, destination)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise

        await asyncio.to_thread(write_file)

    async def load(self, filename: str) -> bytes:
        path = self._path_for(filename)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise ImageNotFoundError(filename) from exc

    async def delete(self, filename: str) -> None:
        path = self._path_for(filename)
        await asyncio.to_thread(path.unlink, missing_ok=True)


def get_image_storage_service() -> ImageStorageService:
    """Dependency boundary: replace only this factory to switch to S3 later."""
    return LocalImageStorageService(settings.storage_path)
