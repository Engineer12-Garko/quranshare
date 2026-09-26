"""History route — GET /history."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.posting_history import HistoryListResponse
from app.services.history import list_history

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
def get_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's posting history, newest first."""
    items, total = list_history(db, current_user.id, skip=skip, limit=limit)
    return HistoryListResponse(items=items, total=total, skip=skip, limit=limit)
