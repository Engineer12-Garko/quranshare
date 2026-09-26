"""
Tests for GET /progress/weekly.
"""
from datetime import datetime, timezone, timedelta

from app.models.posting_history import PostingHistory
from app.models.user import User
from app.models.video import Video
from app.utils.security import hash_password


def _seed_user(db, email="prog@example.com"):
    u = User(
        email=email,
        password_hash=hash_password("Secret123"),
        display_name="Prog User",
        role="user",
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _seed_video(db, fid="progvid1"):
    v = Video(drive_file_id=fid, title="Prog Vid", is_active=True)
    db.add(v)
    db.flush()
    return v


def _post_history(db, user_id, video_id, action="posted", days_ago=0):
    ph = PostingHistory(
        user_id=user_id,
        video_id=video_id,
        action=action,
        posted_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(ph)
    db.flush()


def _set_session(client, user_id):
    from itsdangerous import URLSafeSerializer
    from app.config import settings
    s = URLSafeSerializer(settings.secret_key, salt="session")
    client.cookies.set("session", s.dumps({"user_id": user_id}))


def test_weekly_progress_requires_auth(client):
    resp = client.get("/api/v1/progress/weekly")
    assert resp.status_code == 401


def test_weekly_progress_empty(client, db):
    u = _seed_user(db)
    _set_session(client, u.id)
    resp = client.get("/api/v1/progress/weekly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_posted"] == 0
    assert data["goal"] == 7
    assert len(data["days"]) == 7


def test_weekly_progress_counts_posted_only(client, db):
    u = _seed_user(db, email="progp@example.com")
    v = _seed_video(db, fid="progvid2")
    _set_session(client, u.id)
    # Post today and 1 day ago
    _post_history(db, u.id, v.id, action="posted", days_ago=0)
    _post_history(db, u.id, v.id, action="posted", days_ago=1)
    # A share_initiated should NOT count
    _post_history(db, u.id, v.id, action="share_initiated", days_ago=0)
    resp = client.get("/api/v1/progress/weekly")
    assert resp.status_code == 200
    assert resp.json()["total_posted"] == 2


def test_weekly_progress_shape(client, db):
    u = _seed_user(db, email="progs@example.com")
    _set_session(client, u.id)
    data = client.get("/api/v1/progress/weekly").json()
    assert "week_start" in data
    assert "week_end" in data
    assert "days" in data
    assert "total_posted" in data
    assert "goal" in data
    day = data["days"][0]
    assert "date" in day
    assert "posted" in day
    assert "count" in day
