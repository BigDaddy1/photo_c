import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ImageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    width: int
    height: int
    created_at: datetime
    updated_at: datetime


class ImageList(BaseModel):
    items: list[ImageSummary]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class HealthResponse(BaseModel):
    status: str
