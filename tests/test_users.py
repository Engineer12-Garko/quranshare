"""
Tests for GET /users/me and PATCH /users/me.
"""
from app.models.user import User
from app.utils.security import hash_password


def _seed_user(db, email="u@example.com", display_name="Test", whatsapp=None):
    u = User(
        email=email,
        password_hash=hash_password("Secret123"),
        display_name=display_name,
        whatsapp_number=whatsapp,
        role="user",
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


def test_get_me_returns_profile(client, db):
    u = _seed_user(db)
    _set_session(client, u.id)
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "u@example.com"


def test_get_me_unauthenticated_returns_401(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_patch_me_display_name(client, db):
    u = _seed_user(db, display_name="Old Name")
    _set_session(client, u.id)
    resp = client.patch("/api/v1/users/me", json={"display_name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Name"


def test_patch_me_whatsapp(client, db):
    u = _seed_user(db)
    _set_session(client, u.id)
    resp = client.patch("/api/v1/users/me", json={"whatsapp_number": "+447700000000"})
    assert resp.status_code == 200
    assert resp.json()["whatsapp_number"] == "+447700000000"


def test_patch_me_empty_body_is_noop(client, db):
    u = _seed_user(db, display_name="Unchanged")
    _set_session(client, u.id)
    resp = client.patch("/api/v1/users/me", json={})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Unchanged"


def test_patch_me_unauthenticated_returns_401(client):
    resp = client.patch("/api/v1/users/me", json={"display_name": "X"})
    assert resp.status_code == 401
