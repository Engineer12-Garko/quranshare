"""Video routes — list, detail, stream, share, posted."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.posting_history import PostHistoryResponse
from app.schemas.video import VideoListResponse, VideoResponse
from app.services.history import record_posted, record_share
from app.services.videos import get_video, list_videos, stream_video

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
def get_videos(
    category_id: int | None = Query(default=None, description="Filter by category ID"),
    search: str | None = Query(default=None, description="Search in title/description"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List active videos with optional category filter and text search."""
    items, total = list_videos(db, category_id=category_id, search=search, skip=skip, limit=limit)
    return VideoListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{video_id}", response_model=VideoResponse)
def get_video_by_id(video_id: int, db: Session = Depends(get_db)):
    """Return a single active video by ID."""
    return get_video(db, video_id)


@router.get("/{video_id}/stream")
def stream(
    video_id: int,
    range: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Proxy the MP4 from Google Drive to the browser.
    Supports HTTP Range requests for seek support.
    """
    return stream_video(db, video_id, range_header=range)


@router.post("/{video_id}/share", response_model=PostHistoryResponse, status_code=status.HTTP_201_CREATED)
def share_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record that the authenticated user initiated a WhatsApp share."""
    return record_share(db, current_user.id, video_id)


@router.post("/{video_id}/posted", response_model=PostHistoryResponse, status_code=status.HTTP_201_CREATED)
def mark_posted(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record that the user explicitly confirmed they posted the video to WhatsApp.
    This is the only action that creates a posting_history record (share ≠ posted).
    """
    return record_posted(db, current_user.id, video_id)
