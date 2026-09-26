"""Pydantic schemas for video request and response bodies."""
from datetime import datetime

from pydantic import BaseModel, Field


class VideoResponse(BaseModel):
    id: int
    drive_file_id: str
    title: str
    description: str | None
    category_id: int | None
    duration_seconds: int | None
    drive_web_view_link: str | None
    drive_download_link: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    skip: int
    limit: int
