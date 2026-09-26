"""Users route — GET /users/me, PATCH /users/me."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UpdateProfileRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's display name and/or WhatsApp number."""
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.whatsapp_number is not None:
        current_user.whatsapp_number = payload.whatsapp_number
    db.commit()
    db.refresh(current_user)
    return current_user
