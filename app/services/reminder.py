"""Reminder service — pick a daily video excluding recently shared ones."""
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.posting_history import PostingHistory
from app.models.video import Video


def get_today_reminder(db: Session, user_id: int) -> Video:
    """
    Return the next video in the user's queue.
    The queue prioritizes active videos that have never been posted,
    ordered by how recently they were added (newest first).
    If all videos have been posted, it cycles back to the video
    that was posted the longest time ago (FIFO for repeats).
    """
    # 1. Subquery for all videos the user has EVER posted
    posted_subq = (
        db.query(PostingHistory.video_id)
        .filter(PostingHistory.user_id == user_id)
        .filter(PostingHistory.action == "posted")
    ).subquery()

    # 2. Try to find an unposted video (FIFO queue: oldest unseen videos first)
    candidate = (
        db.query(Video)
        .filter(Video.is_active.is_(True))
        .filter(Video.id.not_in(posted_subq))
        .order_by(Video.created_at.asc())
        .first()
    )

    if candidate:
        return candidate

    # 3. If all active videos are posted, repeat the one posted longest ago
    most_recent_posts = (
        db.query(
            PostingHistory.video_id,
            func.max(PostingHistory.posted_at).label('last_posted')
        )
        .filter(PostingHistory.user_id == user_id)
        .filter(PostingHistory.action == "posted")
        .group_by(PostingHistory.video_id)
        .subquery()
    )

    candidate = (
        db.query(Video)
        .join(most_recent_posts, Video.id == most_recent_posts.c.video_id)
        .filter(Video.is_active.is_(True))
        .order_by(most_recent_posts.c.last_posted.asc())
        .first()
    )

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No videos available.",
        )

    return candidate
