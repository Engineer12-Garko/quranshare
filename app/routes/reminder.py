"""Reminder route — GET /reminders/today."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.video import VideoResponse
from app.services.reminder import get_today_reminder

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("/today", response_model=VideoResponse)
def today_reminder(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a random video for today's reminder, excluding recently shared ones."""
    return get_today_reminder(db, current_user.id)
