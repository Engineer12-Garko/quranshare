"""Progress route — GET /progress/weekly."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.progress import WeeklyProgressResponse
from app.services.progress import get_weekly_progress

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/weekly", response_model=WeeklyProgressResponse)
def weekly_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current week's posting progress for the authenticated user."""
    return get_weekly_progress(db, current_user.id)
