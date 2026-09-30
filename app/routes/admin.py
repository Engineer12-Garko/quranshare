"""Admin routes — Drive sync and user management."""
import time
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.user import UserResponse, AdminUpdateUserRequest
import csv
import io
from fastapi.responses import StreamingResponse
from app.services.sync import sync_drive

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_role("admin")
_curator_or_admin = require_role("curator", "admin")


# ── Vercel Cron Endpoint ────────────────────────────────────────────────
# This endpoint is triggered by Vercel Cron Jobs every 15 minutes.
# It uses a secret-based authentication mechanism:
# - Vercel adds a `x-vercel-cron` header to cron-triggered requests
# - The secret is configured in Vercel environment variables
# - The endpoint does NOT require a QuranFlow user session
# - It reuses the existing sync_drive() service
# - Manual admin sync (for debugging/recovery) is retained separately

import os


@router.post("/sync/google-drive-cron")
def trigger_sync_cron(
    x_vercel_cron: str = Header(None),
    db: Session = Depends(get_db),
):
    """Vercel Cron-triggered Google Drive sync.

    Triggers sync_drive() when invoked by Vercel Cron Jobs.
    Authentication: Vercel adds x-vercel-cron header to scheduled requests.
    No QuranFlow user session required. Idempotent: repeated runs preserve existing state.
    Returns: sync summary dict.
    """
    # Verify cron secret against environment variable (read at request time for testability)
    expected_secret = os.getenv("VERCEL_CRON_SECRET", "")
    if not expected_secret or x_vercel_cron != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")

    # Run the sync (no user auth required)
    try:
        result = sync_drive(db)
        # Add cron metadata to result
        result["_cron_triggered"] = True
        result["_cron_timestamp"] = int(time.time())
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "_cron_triggered": True,
            "_cron_timestamp": int(time.time()),
        }


# ── Manual Admin Sync ──────────────────────────────────────────────────
# Accessible to users with role 'curator' or 'admin'.
# Requires proper authentication session.
# For debugging and manual recovery only.
# Returns a summary: added, updated, deactivated, failed.

@router.post("/sync/google-drive")
def trigger_sync(
    db: Session = Depends(get_db),
    _: User = Depends(_curator_or_admin),
):
    """Manual Google Drive sync.

    Accessible to users with role 'curator' or 'admin'.
    Requires proper authentication session.
    For debugging and manual recovery only.
    Returns a summary: added, updated, deactivated, failed.
    """
    return sync_drive(db)


# ── User Management ──────────────────────────────────────────────────────

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
        writer.writerow(
            [
                u.id,
                u.display_name,
                u.email,
                u.whatsapp_number or "",
                u.gender or "",
                u.role,
                "Yes" if u.is_active else "No",
                u.created_at.isoformat(),
            ]
        )

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
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
        raise HTTPException(status_code=404, detail="User not found")

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
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return None