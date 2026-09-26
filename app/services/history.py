"""Posting history service."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.posting_history import PostingHistory
from app.models.video import Video


def record_share(db: Session, user_id: int, video_id: int) -> PostingHistory:
    """Record that the user initiated a share. Raises 404 if video is inactive/missing."""
    _require_active_video(db, video_id)
    return _create_entry(db, user_id, video_id, action="share_initiated")


def record_posted(db: Session, user_id: int, video_id: int) -> PostingHistory:
    """Record that the user explicitly confirmed a post. Creates the posting_history row."""
    _require_active_video(db, video_id)
    return _create_entry(db, user_id, video_id, action="posted")


def list_history(
    db: Session, user_id: int, skip: int = 0, limit: int = 20
) -> tuple[list[PostingHistory], int]:
    """Return (items, total) of the user's own posting history, newest first."""
    q = (
        db.query(PostingHistory)
        .filter(PostingHistory.user_id == user_id)
        .order_by(PostingHistory.posted_at.desc())
    )
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return items, total


# ── helpers ────────────────────────────────────────────────────────────────────

def _require_active_video(db: Session, video_id: int) -> None:
    video = db.query(Video).filter(Video.id == video_id, Video.is_active.is_(True)).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")


def _create_entry(db: Session, user_id: int, video_id: int, action: str) -> PostingHistory:
    entry = PostingHistory(user_id=user_id, video_id=video_id, action=action)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
