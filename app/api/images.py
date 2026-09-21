import asyncio
import uuid
from pathlib import Path
from typing import Annotated, ClassVar

from fastapi import Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select

from app.api.base import APIView
from app.config import settings
from app.db.models import ImageRecord
from app.schemas import ImageList, ImageSummary
from app.services.image_storage import (
    ImageNotFoundError,
    ImageStorageService,
    get_image_storage_service,
)
from app.services.palette import ImageTooLargeError, InvalidJpegError, analyse_jpeg

Storage = Annotated[ImageStorageService, Depends(get_image_storage_service)]
UPLOAD_READ_CHUNK_BYTES = 1024 * 1024


async def read_upload_content(file: UploadFile) -> bytes:
    """Read an upload incrementally without exceeding the configured byte limit."""
    content = bytearray()
    while chunk := await file.read(UPLOAD_READ_CHUNK_BYTES):
        if len(content) + len(chunk) > settings.max_upload_bytes:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File is too large")
        content.extend(chunk)
    return bytes(content)


async def get_image_or_404(image_id: uuid.UUID) -> ImageRecord:
    image = await ImageRecord.get(image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image


class ImageUploadView(APIView):
    url: ClassVar[str] = "/images"
    methods: ClassVar[tuple[str, ...]] = ("post",)
    kwargs: ClassVar[dict[str, object]] = {
        "status_code": status.HTTP_201_CREATED,
        "response_model": ImageSummary,
    }

    async def post(
        self,
        storage: Storage,
        file: Annotated[UploadFile, File(description="JPEG image to upload")],
    ) -> ImageRecord:
        content = await read_upload_content(file)
        if not content:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is empty")

        try:
            width, height, palette = await asyncio.to_thread(
                analyse_jpeg,
                content,
                max_pixels=settings.max_image_pixels,
            )
        except ImageTooLargeError as exc:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
        except InvalidJpegError as exc:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc

        stored_filename = f"{uuid.uuid4()}.jpg"
        await storage.save(stored_filename, content)
        try:
            image = ImageRecord(
                original_filename=Path(file.filename or "upload.jpg").name,
                stored_filename=stored_filename,
                width=width,
                height=height,
                palette=palette,
            )
            await image.create()
            return image
        except Exception:
            await storage.delete(stored_filename)
            raise


class ImageListView(APIView):
    url: ClassVar[str] = "/images"
    methods: ClassVar[tuple[str, ...]] = ("get",)
    kwargs: ClassVar[dict[str, object]] = {"response_model": ImageList}

    async def get(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ImageList:
        images = await ImageRecord.select(
            select(ImageRecord).order_by(ImageRecord.created_at.desc()).limit(limit).offset(offset)
        )
        return ImageList(items=images, limit=limit, offset=offset)


class ImageDetailView(APIView):
    url: ClassVar[str] = "/images/{image_id}"
    methods: ClassVar[tuple[str, ...]] = ("get", "delete")
    method_kwargs: ClassVar[dict[str, dict[str, object]]] = {
        "get": {"response_model": ImageSummary},
        "delete": {"status_code": status.HTTP_204_NO_CONTENT},
    }

    async def get(self, image_id: uuid.UUID) -> ImageRecord:
        return await get_image_or_404(image_id)

    async def delete(self, image_id: uuid.UUID, storage: Storage) -> Response:
        images = await ImageRecord.delete(ImageRecord.id == image_id)
        if not images:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
        image = images[0]
        # Metadata is deleted first to keep the database and RGB aggregate transactionally
        # consistent. If storage deletion fails, an orphan file can remain; production should
        # add a transactional outbox and retry worker to de-orphan stored files.
        await storage.delete(image.stored_filename)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


class ImagePaletteView(APIView):
    url: ClassVar[str] = "/images/{image_id}/palette"
    methods: ClassVar[tuple[str, ...]] = ("get",)
    kwargs: ClassVar[dict[str, object]] = {"response_model": list[str]}

    async def get(self, image_id: uuid.UUID) -> list[str]:
        image = await get_image_or_404(image_id)
        return image.palette


class ImageFileView(APIView):
    url: ClassVar[str] = "/images/{image_id}/file"
    methods: ClassVar[tuple[str, ...]] = ("get",)

    async def get(self, image_id: uuid.UUID, storage: Storage) -> Response:
        image = await get_image_or_404(image_id)
        try:
            content = await storage.load(image.stored_filename)
        except ImageNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found")
        return Response(
            content=content,
            media_type=image.content_type,
            headers={"Content-Disposition": f'attachment; filename="{image.original_filename}"'},
        )
