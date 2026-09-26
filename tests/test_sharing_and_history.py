"""
Tests for POST /videos/{id}/share, POST /videos/{id}/posted,
GET /history, and GET /reminders/today (updated prefix).
"""
from app.models.posting_history import PostingHistory
from app.models.user import User
from app.models.video import Video
from app.utils.security import hash_password


def _seed_user(db, email="vop@example.com", role="user"):
    u = User(
        email=email,
        password_hash=hash_password("Secret123"),
        display_name="VOP User",
        role=role,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _seed_video(db, fid="vopvid1"):
    v = Video(drive_file_id=fid, title="VOP Vid", is_active=True)
    db.add(v)
    db.flush()
    return v


def _set_session(client, user_id):
    from itsdangerous import URLSafeSerializer
    from app.config import settings
    s = URLSafeSerializer(settings.secret_key, salt="session")
    client.cookies.set("session", s.dumps({"user_id": user_id}))


# ── POST /videos/{id}/share ────────────────────────────────────────────────────

def test_share_requires_auth(client, db):
    v = _seed_video(db, "sv1")
    resp = client.post(f"/api/v1/videos/{v.id}/share")
    assert resp.status_code == 401


def test_share_creates_share_initiated_record(client, db):
    u = _seed_user(db, "share1@example.com")
    v = _seed_video(db, "sv2")
    _set_session(client, u.id)
    resp = client.post(f"/api/v1/videos/{v.id}/share")
    assert resp.status_code == 201
    assert resp.json()["action"] == "share_initiated"


def test_share_does_not_equal_posted(client, db):
    """share ≠ posted: sharing should NOT create a 'posted' record."""
    u = _seed_user(db, "share2@example.com")
    v = _seed_video(db, "sv3")
    _set_session(client, u.id)
    client.post(f"/api/v1/videos/{v.id}/share")
    # Check the record action is share_initiated, not posted
    record = db.query(PostingHistory).filter_by(user_id=u.id, video_id=v.id).first()
    assert record.action == "share_initiated"


def test_share_nonexistent_video_returns_404(client, db):
    u = _seed_user(db, "share3@example.com")
    _set_session(client, u.id)
    resp = client.post("/api/v1/videos/99999/share")
    assert resp.status_code == 404


# ── POST /videos/{id}/posted ───────────────────────────────────────────────────

def test_posted_requires_auth(client, db):
    v = _seed_video(db, "pv1")
    resp = client.post(f"/api/v1/videos/{v.id}/posted")
    assert resp.status_code == 401


def test_posted_creates_posted_record(client, db):
    u = _seed_user(db, "posted1@example.com")
    v = _seed_video(db, "pv2")
    _set_session(client, u.id)
    resp = client.post(f"/api/v1/videos/{v.id}/posted")
    assert resp.status_code == 201
    assert resp.json()["action"] == "posted"
    assert resp.json()["user_id"] == u.id
    assert resp.json()["video_id"] == v.id


def test_posted_nonexistent_video_returns_404(client, db):
    u = _seed_user(db, "posted2@example.com")
    _set_session(client, u.id)
    resp = client.post("/api/v1/videos/99999/posted")
    assert resp.status_code == 404


# ── GET /history ───────────────────────────────────────────────────────────────

def test_get_history_requires_auth(client):
    resp = client.get("/api/v1/history")
    assert resp.status_code == 401


def test_get_history_returns_own_records(client, db):
    u = _seed_user(db, "hist1@example.com")
    v = _seed_video(db, "hv1")
    _set_session(client, u.id)
    client.post(f"/api/v1/videos/{v.id}/posted")
    resp = client.get("/api/v1/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "posted"


def test_get_history_does_not_return_other_users_records(client, db):
    u1 = _seed_user(db, "hist2a@example.com")
    u2 = _seed_user(db, "hist2b@example.com")
    v = _seed_video(db, "hv2")
    # Log entry for u1
    ph = PostingHistory(user_id=u1.id, video_id=v.id, action="posted")
    db.add(ph)
    db.flush()
    # u2 should see empty history
    _set_session(client, u2.id)
    resp = client.get("/api/v1/history")
    assert resp.json()["total"] == 0


def test_get_history_pagination(client, db):
    u = _seed_user(db, "histp@example.com")
    for i in range(5):
        v = _seed_video(db, f"hpv{i}")
        ph = PostingHistory(user_id=u.id, video_id=v.id, action="posted")
        db.add(ph)
    db.flush()
    _set_session(client, u.id)
    resp = client.get("/api/v1/history?skip=0&limit=3")
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5


# ── GET /reminders/today (prefix correction check) ────────────────────────────

def test_reminders_today_uses_correct_prefix(client, db):
    u = _seed_user(db, "rem@example.com")
    v = _seed_video(db, "remvid1")
    _set_session(client, u.id)
    resp = client.get("/api/v1/reminders/today")
    assert resp.status_code == 200
    # Old prefix /reminder/today (singular) is not an API route — SPA catch-all returns HTML
    resp_old = client.get("/api/v1/reminder/today")
    assert resp_old.status_code != 401  # not an auth-protected API endpoint
    ct = resp_old.headers.get("content-type", "")
    assert "application/json" not in ct or resp_old.json().get("status") != "ok"
