"""Tests for Vercel Cron sync endpoint."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.utils.security import hash_password

# Set cron secret for testing
os.environ["VERCEL_CRON_SECRET"] = "test-secret"


def _seed_admin(db):
    """Seed an admin user for testing."""
    admin = User(
        email="cronadmin@test.com",
        password_hash=hash_password("Secret123"),
        display_name="Cron Admin",
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.flush()
    return admin


def _seed_user(db, email="cronuser@test.com"):
    """Seed a normal user for testing."""
    user = User(
        email=email,
        password_hash=hash_password("Secret123"),
        display_name="Normal User",
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _set_session(client, user_id):
    """Set session cookie for a user."""
    from itsdangerous import URLSafeSerializer
    from app.config import settings
    s = URLSafeSerializer(settings.secret_key, salt="session")
    client.cookies.set("session", s.dumps({"user_id": user_id}))


# ── Cron endpoint tests ────────────────────────────────────────────────


def test_cron_sync_requires_cron_secret(client):
    """Cron endpoint must reject requests without valid cron secret."""
    resp = client.post("/api/v1/admin/sync/google-drive-cron")
    assert resp.status_code == 403


def test_cron_sync_rejects_normal_user(client, db):
    """Normal users cannot trigger cron sync even with session."""
    user = _seed_user(db)
    _set_session(client, user.id)
    resp = client.post("/api/v1/admin/sync/google-drive-cron")
    assert resp.status_code == 403


def test_cron_sync_rejects_admin_user_without_cron_secret(client, db):
    """Admin users cannot trigger cron sync without cron secret."""
    admin = _seed_admin(db)
    _set_session(client, admin.id)
    resp = client.post("/api/v1/admin/sync/google-drive-cron")
    assert resp.status_code == 403


def test_cron_sync_accepts_valid_cron_secret(client, db):
    """Cron endpoint accepts requests with valid cron secret."""
    resp = client.post(
        "/api/v1/admin/sync/google-drive-cron",
        headers={"x-vercel-cron": "test-secret"},
    )
    # Should not be 403 — should proceed to sync (which may fail due to no Drive config)
    assert resp.status_code != 403


def test_cron_sync_does_not_require_user_session(client):
    """Cron endpoint does not require a QuranFlow user session."""
    # No session cookie set
    resp = client.post(
        "/api/v1/admin/sync/google-drive-cron",
        headers={"x-vercel-cron": "test-secret"},
    )
    # Should not be 401 — cron endpoint doesn't check user session
    assert resp.status_code != 401


def test_cron_sync_returns_sync_summary(client, db):
    """Cron endpoint returns sync summary when authorized."""
    resp = client.post(
        "/api/v1/admin/sync/google-drive-cron",
        headers={"x-vercel-cron": "test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    assert "_cron_triggered" in data
    assert data["_cron_triggered"] is True


def test_cron_sync_does_not_accept_user_id_in_body(client):
    """Cron endpoint must not accept user_id from request body."""
    resp = client.post(
        "/api/v1/admin/sync/google-drive-cron",
        headers={"x-vercel-cron": "test-secret"},
        json={"user_id": 1, "role": "admin"},
    )
    # Should still work — body params are ignored
    assert resp.status_code == 200


# ── Manual admin sync tests (retained) ─────────────────────────────────


def test_manual_sync_requires_auth(client):
    """Manual sync endpoint requires authentication."""
    resp = client.post("/api/v1/admin/sync/google-drive")
    assert resp.status_code == 401


def test_manual_sync_requires_admin_role(client, db):
    """Manual sync endpoint requires admin or curator role."""
    user = _seed_user(db)
    _set_session(client, user.id)
    resp = client.post("/api/v1/admin/sync/google-drive")
    assert resp.status_code == 403


def test_manual_sync_works_for_admin(client, db):
    """Manual sync endpoint works for admin users."""
    admin = _seed_admin(db)
    _set_session(client, admin.id)
    resp = client.post("/api/v1/admin/sync/google-drive")
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
