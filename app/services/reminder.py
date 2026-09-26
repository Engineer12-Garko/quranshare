"""Reminder service — pick a daily video excluding recently shared ones."""
import random
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.posting_history import PostingHistory
from app.models.video import Video


def get_today_reminder(db: Session, user_id: int) -> Video:
    """
    Return a random active video, excluding the most recently shared
    `settings.recent_exclusion_limit` videos for this user.
    Raises 404 if no eligible videos exist.
    """
    # IDs of videos this user has recently shared, most recent first
    recent_subq = (
        db.query(PostingHistory.video_id)
        .filter(PostingHistory.user_id == user_id)
        .order_by(PostingHistory.posted_at.desc())
        .limit(settings.recent_exclusion_limit)
        .scalar_subquery()
    )

    candidates = (
        db.query(Video)
        .filter(Video.is_active.is_(True))
        .filter(Video.id.not_in(recent_subq))
        .all()
    )

    if not candidates:
        # Fall back to all active videos when every video has been recently shared
        candidates = db.query(Video).filter(Video.is_active.is_(True)).all()

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No videos available.",
        )

    return random.choice(candidates)
