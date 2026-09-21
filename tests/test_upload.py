from io import BytesIO

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api.images import read_upload_content
from app.config import settings


@pytest.mark.asyncio
async def test_upload_reader_rejects_a_file_larger_than_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_upload_bytes", 3)
    upload = UploadFile(filename="large.jpg", file=BytesIO(b"abcd"))

    with pytest.raises(HTTPException) as exception:
        await read_upload_content(upload)

    assert exception.value.status_code == 413
