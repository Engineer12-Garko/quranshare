"""Reminder service — deterministic daily video rotation."""
import hashlib
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.posting_history import PostingHistory
from app.models.video import Video


def get_today_reminder(db: Session, user_id: int) -> Video:
    """
    Return a deterministic daily video for the user.

    Selection rules:
    1. Get all active videos.
    2. Exclude videos posted in the last `recent_exclusion_limit` days.
    3. Use user_id + current_date as a deterministic seed to select one video.
    4. Same user + same date = same video (stable across refreshes).
    5. Different date = normally different video (rotation).
    6. Avoid yesterday's recommendation when multiple candidates exist.
    """
    today = date.today()

    # 1. Get all active videos
    active_videos = (
        db.query(Video)
        .filter(Video.is_active.is_(True))
        .order_by(Video.id.asc())
        .all()
    )

    if not active_videos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No videos available.",
        )

    # 2. Exclude recently posted videos (existing rule)
    recent_exclusion_limit = settings.recent_exclusion_limit
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=recent_exclusion_limit)
    recent_posted_ids = (
        db.query(PostingHistory.video_id)
        .filter(PostingHistory.user_id == user_id)
        .filter(PostingHistory.action == "posted")
        .filter(PostingHistory.posted_at >= cutoff_date)
        .all()
    )
    recent_ids = {row[0] for row in recent_posted_ids}

    eligible = [v for v in active_videos if v.id not in recent_ids]

    # 3. Fallback: if all videos were recently posted, use all active videos
    if not eligible:
        eligible = active_videos

    # 4. Deterministic daily selection using user_id + date as seed
    seed_data = f"{user_id}:{today.isoformat()}"
    seed_hash = hashlib.sha256(seed_data.encode()).hexdigest()
    seed_int = int(seed_hash[:8], 16)

    # 5. Try to avoid yesterday's recommendation
    yesterday = date.fromordinal(today.toordinal() - 1)
    yesterday_seed = f"{user_id}:{yesterday.isoformat()}"
    yesterday_hash = hashlib.sha256(yesterday_seed.encode()).hexdigest()
    yesterday_int = int(yesterday_hash[:8], 16)
    yesterday_idx = yesterday_int % len(eligible)

    # Select index, avoiding yesterday's choice when possible
    selected_idx = seed_int % len(eligible)
    if len(eligible) > 1 and selected_idx == yesterday_idx:
        selected_idx = (selected_idx + 1) % len(eligible)

    return eligible[selected_idx]
