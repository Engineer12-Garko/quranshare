"""Admin routes — Drive sync and user management."""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.user import UserResponse, AdminUpdateUserRequest
import csv
import io
from fastapi.responses import StreamingResponse
from app.services.sync import sync_drive

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_role("admin")
_curator_or_admin = require_role("curator", "admin")


@router.post("/sync/google-drive")
def trigger_sync(
    db: Session = Depends(get_db),
    _: User = Depends(_curator_or_admin),
):
    """
    Synchronise Google Drive content into the videos table.
    Accessible to users with role 'curator' or 'admin'.
    Returns a summary: added, updated, deactivated, failed.
    """
    return sync_drive(db)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(_admin_only),
):
    """Return all registered users. Admin only."""
    return db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/users/csv")
def download_users_csv(
    db: Session = Depends(get_db),
    _: User = Depends(_admin_only),
):
    """Download all users as a CSV file."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "WhatsApp", "Gender", "Role", "Active", "Joined"])
    
    for u in users:
        writer.writerow([
            u.id,
            u.display_name,
            u.email,
            u.whatsapp_number or "",
            u.gender or "",
            u.role,
            "Yes" if u.is_active else "No",
            u.created_at.isoformat()
        ])
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    req: AdminUpdateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_admin_only),
):
    """Update a user's role or status. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    
    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
        
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_admin_only),
):
    """Delete a user. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        
    db.delete(user)
    db.commit()
    return None
