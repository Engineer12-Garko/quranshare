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


# ── Vercel Cron / Scheduler Endpoint ────────────────────────────────────
# Triggered by an external scheduler (GitHub Actions workflow) every 15
# minutes, and optionally by Vercel Cron on paid plans.
# It uses a secret-based authentication mechanism:
# - The scheduler sends the secret in an `Authorization: Bearer <secret>`
#   header (Vercel-native style) or an `x-vercel-cron` header.
# - The secret is configured via the CRON_SECRET (preferred) or
#   VERCEL_CRON_SECRET environment variable.
# - The endpoint does NOT require a QuranFlow user session
# - It reuses the existing sync_drive() service
# - Manual admin sync (for debugging/recovery) is retained separately

import os


def _expected_cron_secret() -> str:
    """Read the cron secret at request time so it can be rotated/tested."""
    return os.getenv("CRON_SECRET") or os.getenv("VERCEL_CRON_SECRET", "")


@router.get("/sync/google-drive-cron", include_in_schema=False)
@router.post("/sync/google-drive-cron")
def trigger_sync_cron(
    x_vercel_cron: str = Header(None),
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Scheduler-triggered Google Drive sync.

    Triggers sync_drive() when invoked by an external scheduler or Vercel Cron.
    Authentication: a shared secret sent as `Authorization: Bearer <secret>`
    or `x-vercel-cron: <secret>`, compared against CRON_SECRET
    (or VERCEL_CRON_SECRET for backwards compatibility).
    No QuranFlow user session required. Idempotent: repeated runs preserve existing state.
    Returns: sync summary dict.
    """
    # Verify cron secret against environment variable (read at request time for testability)
    expected_secret = _expected_cron_secret()
    provided_secret = x_vercel_cron or ""
    if authorization and authorization.startswith("Bearer "):
        provided_secret = authorization[len("Bearer "):]
    if not expected_secret or provided_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")

    # Run the sync (no user auth required)
    try:
        result = sync_drive(db)
        # Add cron metadata to result
        result["_cron_triggered"] = True
        result["_cron_timestamp"] = int(time.time())
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Drive sync failed unexpectedly.",
        ) from exc


# ── Emergency Manual Sync ─────────────────────────────────────────────
# Accessible to users with role 'curator' or 'admin'.
# Requires proper authentication session.
# For debugging and emergency recovery only; normal updates use the scheduler.
# Returns a summary: added, updated, deactivated, failed.

@router.post("/sync/google-drive")
def trigger_sync(
    db: Session = Depends(get_db),
    _: User = Depends(_curator_or_admin),
):
    """Emergency manual Google Drive sync.

    Accessible to users with role 'curator' or 'admin'.
    Requires proper authentication session.
    Normal catalog updates are handled automatically by the scheduler.
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
