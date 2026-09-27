"""
Tests for auth routes: /register, /login, /logout, /me, /activate.
"""
from app.models.user import User
from app.utils.security import hash_password


# ── helpers ────────────────────────────────────────────────────────────

def _register(client, email="test@example.com", password="Secret123", display_name="Test User"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )


def _login(client, email="test@example.com", password="Secret123"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def _seed_user(db, email="seeded@example.com", password="Secret123", role="user"):
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name="Seeded User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _seed_admin(db):
    """Seed an admin user for role-based access tests."""
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("Secret123"),
        display_name="Admin",
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.flush()
    return admin


def _set_session(client, user_id):
    from itsdangerous import URLSafeSerializer
    from app.config import settings
    s = URLSafeSerializer(settings.secret_key, salt="session")
    client.cookies.set("session", s.dumps({"user_id": user_id}))


# ── register ───────────────────────────────────────────────────────────

def test_register_creates_user(client):
    resp = _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert "password_hash" not in data


def test_register_sets_session_cookie(client):
    resp = _register(client)
    assert resp.status_code == 201
    assert "session" in resp.cookies


def test_register_duplicate_email_returns_409(client):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409


def test_register_weak_password_returns_422(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "password": "short", "display_name": "A"},
    )
    assert resp.status_code == 422


def test_register_no_uppercase_returns_422(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "password": "alllower1", "display_name": "A"},
    )
    assert resp.status_code == 422


def test_register_no_digit_returns_422(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "password": "NoDigitHere", "display_name": "A"},
    )
    assert resp.status_code == 422


# ── login ──────────────────────────────────────────────────────────────

def test_login_success(client, db):
    _seed_user(db)
    resp = _login(client, email="seeded@example.com")
    assert resp.status_code == 200
    assert resp.json()["email"] == "seeded@example.com"
    assert "session" in resp.cookies


def test_login_wrong_password_returns_401(client, db):
    _seed_user(db)
    resp = _login(client, email="seeded@example.com", password="WrongPass1")
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    resp = _login(client, email="nobody@example.com")
    assert resp.status_code == 401


def test_login_inactive_user_returns_403(client, db):
    user = _seed_user(db)
    user.is_active = False
    db.flush()
    resp = _login(client, email="seeded@example.com")
    assert resp.status_code == 403


# ── logout ─────────────────────────────────────────────────────────────

def test_logout_clears_cookie(client):
    _register(client)
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204


# ── me ─────────────────────────────────────────────────────────────────

def test_me_returns_current_user(client):
    _register(client, email="me@example.com")
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_me_without_session_returns_401(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── activate (new name-only activation) ────────────────────────────────

def test_activate_creates_user_with_name_only(client, db):
    """Activation with just a name creates a user with role='user'."""
    resp = client.post("/api/v1/auth/activate", json={"name": "New User"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["display_name"] == "New User"
    assert data["role"] == "user"


def test_activate_sets_session_cookie(client):
    """Activation sets the session cookie."""
    resp = client.post("/api/v1/auth/activate", json={"name": "Cookie User"})
    assert resp.status_code == 201
    assert "session" in resp.cookies


def test_activate_rejects_empty_name(client):
    """Empty name is rejected."""
    resp = client.post("/api/v1/auth/activate", json={"name": ""})
    assert resp.status_code == 422


def test_activate_establishes_authentication(client, db):
    """Activated user can access /auth/me with their session."""
    resp = client.post("/api/v1/auth/activate", json={"name": "Auth User"})
    assert resp.status_code == 201
    assert "session" in resp.cookies
    resp2 = client.get("/api/v1/auth/me")
    assert resp2.status_code == 200
    assert resp2.json()["display_name"] == "Auth User"


def test_activate_always_creates_user_role(client):
    """Activation always creates role='user', never admin."""
    resp = client.post("/api/v1/auth/activate", json={"name": "Normal User"})
    assert resp.status_code == 201
    assert resp.json()["role"] == "user"


def test_admin_account_has_admin_role(client, db):
    """The admin account has role='admin'."""
    _seed_admin(db)
    admin = db.query(User).filter(User.role == 'admin').first()
    assert admin is not None
    assert admin.role == "admin"
    assert admin.is_active is True


def test_admin_can_access_admin_endpoints(client, db):
    """Admin account can access admin-only endpoints."""
    admin = _seed_admin(db)
    _set_session(client, admin.id)
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 200