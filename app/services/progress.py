"""Progress service — derive weekly posting progress from posting_history."""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.posting_history import PostingHistory
from app.schemas.progress import DayProgress, WeeklyProgressResponse


def get_weekly_progress(db: Session, user_id: int) -> WeeklyProgressResponse:
    """
    Compute the current week's (Mon–Sun) posting progress for a user.
    Derived from posting_history rows with action='posted'.
    No separate table — pure query per DSA/DB spec.
    """
    today = date.today()
    # ISO weekday: Monday=1 … Sunday=7
    week_start = today - timedelta(days=today.isoweekday() - 1)
    week_end = week_start + timedelta(days=6)

    # Fetch all 'posted' rows in this week for this user
    rows = (
        db.query(PostingHistory)
        .filter(
            PostingHistory.user_id == user_id,
            PostingHistory.action == "posted",
            PostingHistory.posted_at >= _day_start(week_start),
            PostingHistory.posted_at <= _day_end(week_end),
        )
        .all()
    )

    # Build a day → count map  O(r) where r = rows returned
    day_counts: dict[date, int] = {}
    for row in rows:
        d = row.posted_at.date()
        day_counts[d] = day_counts.get(d, 0) + 1

    # Build 7-day list
    days: list[DayProgress] = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        count = day_counts.get(d, 0)
        days.append(DayProgress(date=d.isoformat(), posted=count > 0, count=count))

    total_posted = sum(dp.count for dp in days)

    return WeeklyProgressResponse(
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        days=days,
        total_posted=total_posted,
        goal=7,
    )


def _day_start(d: date):
    from datetime import datetime, timezone
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


def _day_end(d: date):
    from datetime import datetime, timezone
    return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
