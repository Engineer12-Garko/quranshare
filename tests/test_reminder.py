"""
Tests for GET /api/v1/reminders/today.
"""
from app.models.posting_history import PostingHistory
from app.models.video import Video
from app.models.user import User
from app.utils.security import hash_password


def _seed_user(db, email="remind@example.com"):
    user = User(
        email=email,
        password_hash=hash_password("Secret123"),
        display_name="Remind User",
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _seed_video(db, title="Reminder Vid", drive_file_id=None):
    vid = Video(
        drive_file_id=drive_file_id or title.replace(" ", "_").lower(),
        title=title,
        is_active=True,
    )
    db.add(vid)
    db.flush()
    return vid


def _set_session(client, user_id: int):
    from itsdangerous import URLSafeSerializer
    from app.config import settings
    s = URLSafeSerializer(settings.secret_key, salt="session")
    token = s.dumps({"user_id": user_id})
    client.cookies.set("session", token)


def test_reminder_requires_auth(client):
    resp = client.get("/api/v1/reminders/today")
    assert resp.status_code == 401


def test_reminder_returns_a_video(client, db):
    user = _seed_user(db)
    _seed_video(db, "Daily Reminder", drive_file_id="daily1")
    _set_session(client, user.id)
    resp = client.get("/api/v1/reminders/today")
    assert resp.status_code == 200
    assert "id" in resp.json()


def test_reminder_excludes_recent(client, db):
    user = _seed_user(db)
    vid1 = _seed_video(db, "Recent Vid", drive_file_id="recent1")
    vid2 = _seed_video(db, "Fresh Vid", drive_file_id="fresh2")

    # Log vid1 as recently shared so it should be excluded
    entry = PostingHistory(user_id=user.id, video_id=vid1.id, action="posted")
    db.add(entry)
    db.flush()

    _set_session(client, user.id)
    # Run several times — should always get vid2 since vid1 is excluded
    for _ in range(10):
        resp = client.get("/api/v1/reminders/today")
        assert resp.status_code == 200
        assert resp.json()["id"] == vid2.id


def test_reminder_falls_back_when_all_recent(client, db):
    """When every video has been recently shared, still return a video."""
    user = _seed_user(db, email="fallback@example.com")
    vid = _seed_video(db, "Only Vid", drive_file_id="only1")
    entry = PostingHistory(user_id=user.id, video_id=vid.id, action="posted")
    db.add(entry)
    db.flush()

    _set_session(client, user.id)
    resp = client.get("/api/v1/reminders/today")
    assert resp.status_code == 200
    assert resp.json()["id"] == vid.id


def test_reminder_404_when_no_videos(client, db):
    user = _seed_user(db, email="novids@example.com")
    _set_session(client, user.id)
    resp = client.get("/api/v1/reminders/today")
    assert resp.status_code == 404
