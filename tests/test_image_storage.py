import asyncio

import pytest

from app.services.image_storage import ImageNotFoundError, LocalImageStorageService


def test_local_storage_saves_loads_and_deletes_a_file(tmp_path) -> None:
    storage = LocalImageStorageService(tmp_path)

    asyncio.run(storage.save("test.jpg", b"jpeg-content"))
    assert asyncio.run(storage.load("test.jpg")) == b"jpeg-content"

    asyncio.run(storage.delete("test.jpg"))
    with pytest.raises(ImageNotFoundError):
        asyncio.run(storage.load("test.jpg"))


def test_local_storage_rejects_directory_traversal(tmp_path) -> None:
    storage = LocalImageStorageService(tmp_path)

    with pytest.raises(ValueError):
        asyncio.run(storage.save("../outside.jpg", b"content"))
