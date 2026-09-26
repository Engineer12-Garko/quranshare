"""
Tests for GET /api/v1/history (listing) — basic coverage.
Full share/posted endpoint tests are in test_sharing_and_history.py.
"""
from app.models.posting_history import PostingHistory
from app.models.user import User
from app.models.video import Video
from app.utils.security import hash_password


def _seed_user(db, email="hist_list@example.com"):
    u = User(
        email=email,
        password_hash=hash_password("Secret123"),
        display_name="Hist List User",
        role="user",
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _seed_video(db, fid="hlvid1"):
    v = Video(drive_file_id=fid, title="HL Video", is_active=True)
    db.add(v)
    db.flush()
    return v


def _set_session(client, user_id):
    from itsdangerous import URLSafeSerializer
    from app.config import settings
    s = URLSafeSerializer(settings.secret_key, salt="session")
    client.cookies.set("session", s.dumps({"user_id": user_id}))


def test_history_list_requires_auth(client):
    resp = client.get("/api/v1/history")
    assert resp.status_code == 401


def test_history_list_returns_items(client, db):
    u = _seed_user(db)
    v = _seed_video(db)
    ph = PostingHistory(user_id=u.id, video_id=v.id, action="posted")
    db.add(ph)
    db.flush()
    _set_session(client, u.id)
    resp = client.get("/api/v1/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "posted"


def test_history_list_empty_for_new_user(client, db):
    u = _seed_user(db, email="new_hist@example.com")
    _set_session(client, u.id)
    resp = client.get("/api/v1/history")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []
