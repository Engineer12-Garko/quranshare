"""Auth service — register, login helpers."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import RegisterRequest
from app.utils.security import hash_password, verify_password


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a new user. Raises 409 if the email is already taken."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )
        
    if payload.whatsapp_number:
        existing_wa = db.query(User).filter(User.whatsapp_number == payload.whatsapp_number).first()
        if existing_wa:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that WhatsApp number already exists.",
            )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        whatsapp_number=payload.whatsapp_number,
        gender=payload.gender,
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Return the user if credentials are valid. Raises 401 otherwise."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )
    return user
