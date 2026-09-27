"""Auth routes — register, login, logout, me, activate."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from itsdangerous import URLSafeSerializer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, RegisterRequest, ActivateRequest, UserResponse
from app.services.auth import authenticate_user, register_user, activate_user

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _make_session_cookie(user_id: int) -> str:
    s = URLSafeSerializer(settings.secret_key, salt="session")
    return s.dumps({"user_id": user_id})


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """DEPRECATED: kept for backward compatibility with existing tests."""
    user = register_user(db, payload)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=_make_session_cookie(user.id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=_COOKIE_MAX_AGE,
    )
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """DEPRECATED: kept for backward compatibility with existing tests."""
    user = authenticate_user(db, payload.email, payload.password)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=_make_session_cookie(user.id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=_COOKIE_MAX_AGE,
    )
    return user


@router.post("/activate", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def activate(payload: ActivateRequest, response: Response, db: Session = Depends(get_db)):
    """Name-only activation. Creates a new user profile with role='user'."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name is required.")
    if len(name) > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name too long.")

    user = activate_user(db, name)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=_make_session_cookie(user.id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=_COOKIE_MAX_AGE,
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(key=_COOKIE_NAME)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user