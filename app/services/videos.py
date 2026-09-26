"""Videos service."""
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.video import Video


def list_videos(
    db: Session,
    category_id: int | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
    active_only: bool = True,
) -> tuple[list[Video], int]:
    """Return (items, total) for paginated video listing with optional search."""
    q = db.query(Video)
    if active_only:
        q = q.filter(Video.is_active.is_(True))
    if category_id is not None:
        q = q.filter(Video.category_id == category_id)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            Video.title.ilike(term) | Video.description.ilike(term)
        )
    total = q.count()
    items = q.order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_video(db: Session, video_id: int) -> Video:
    """Return a single active video or raise 404."""
    video = db.query(Video).filter(Video.id == video_id, Video.is_active.is_(True)).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")
    return video


def stream_video(db: Session, video_id: int, range_header: str | None) -> StreamingResponse:
    """
    Stream an MP4 strictly from Google Drive to the browser.
    """
    from app.services.google_drive import get_drive_service, DriveNotConfiguredError

    video = get_video(db, video_id)
    if not video.drive_file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No file associated.")

    try:
        drive = get_drive_service()
        return drive.stream_file(video.drive_file_id, range_header=range_header)
    except DriveNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video file not available because Google Drive is not configured.",
        )
