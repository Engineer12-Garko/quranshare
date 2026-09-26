"""Pydantic schemas for posting history request and response bodies."""
from datetime import datetime

from pydantic import BaseModel


class PostHistoryResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    action: str
    posted_at: datetime

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    items: list[PostHistoryResponse]
    total: int
    skip: int
    limit: int
