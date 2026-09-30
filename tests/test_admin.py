"""
Tests for admin routes: POST /admin/sync/google-drive, GET /admin/users.
"""
from unittest.mock import MagicMock, patch

from app.models.user import User
from app.utils.security import hash_password


def _seed_user(db, email="admin@example.com", role="admin"):
    u = User(
        email=email,
        password_hash=hash_password("Secret123"),
        display_name="Admin User",
        role=role,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _set_session(client, user_id):
    from itsdangerous import URLSafeSerializer
    from app.config import settings
    s = URLSafeSerializer(settings.secret_key, salt="session")
    client.cookies.set("session", s.dumps({"user_id": user_id}))


# ── GET /admin/users ───────────────────────────────────────────────────────────

def test_admin_users_requires_admin_role(client, db):
    u = _seed_user(db, email="plain@example.com", role="user")
    _set_session(client, u.id)
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 403


def test_admin_users_requires_auth(client):
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 401


def test_admin_users_returns_user_list(client, db):
    admin = _seed_user(db)
    _set_session(client, admin.id)
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "admin@example.com" in emails


def test_curator_cannot_list_users(client, db):
    curator = _seed_user(db, email="cur@example.com", role="curator")
    _set_session(client, curator.id)
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 403


# ── POST /admin/sync/google-drive ──────────────────────────────────────────────

def test_sync_requires_auth(client):
    resp = client.post("/api/v1/admin/sync/google-drive")
    assert resp.status_code == 401


def test_sync_requires_curator_or_admin(client, db):
    u = _seed_user(db, email="plain2@example.com", role="user")
    _set_session(client, u.id)
    resp = client.post("/api/v1/admin/sync/google-drive")
    assert resp.status_code == 403


def test_sync_returns_summary_when_drive_not_configured(client, db):
    admin = _seed_user(db, email="adm2@example.com")
    _set_session(client, admin.id)
    
    from app.services.google_drive import DriveNotConfiguredError
    
    # Drive is not configured in test env — should return failure summary gracefully
    with patch("app.services.google_drive.get_drive_service", side_effect=DriveNotConfiguredError("Not configured")):
        resp = client.post("/api/v1/admin/sync/google-drive")
        
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "error" in data


def test_sync_curator_can_trigger(client, db):
    curator = _seed_user(db, email="cur2@example.com", role="curator")
    _set_session(client, curator.id)
    
    from app.services.google_drive import DriveNotConfiguredError
    
    with patch("app.services.google_drive.get_drive_service", side_effect=DriveNotConfiguredError("Not configured")):
        resp = client.post("/api/v1/admin/sync/google-drive")
        
    assert resp.status_code == 200
    # Returns summary (may be failure due to no Drive config, but not 403)
    assert "success" in resp.json()
