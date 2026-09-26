"""
Tests for GET /api/v1/videos and GET /api/v1/videos/{id}.
"""
from app.models.category import Category
from app.models.video import Video


def _seed_video(db, title="Test Video", drive_file_id=None, category_id=None, is_active=True):
    vid = Video(
        drive_file_id=drive_file_id or title.replace(" ", "_").lower(),
        title=title,
        is_active=is_active,
        category_id=category_id,
    )
    db.add(vid)
    db.flush()
    return vid


def _seed_category(db, name="Cat"):
    cat = Category(name=name, is_active=True)
    db.add(cat)
    db.flush()
    return cat


# ── list ───────────────────────────────────────────────────────────────────────

def test_videos_returns_empty_list(client):
    resp = client.get("/api/v1/videos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_videos_excludes_inactive(client, db):
    _seed_video(db, "Active Vid", drive_file_id="av1", is_active=True)
    _seed_video(db, "Inactive Vid", drive_file_id="iv1", is_active=False)
    resp = client.get("/api/v1/videos")
    data = resp.json()
    titles = [v["title"] for v in data["items"]]
    assert "Active Vid" in titles
    assert "Inactive Vid" not in titles


def test_videos_filter_by_category(client, db):
    cat = _seed_category(db, "Fiqh")
    _seed_video(db, "Fiqh Video", drive_file_id="fv1", category_id=cat.id)
    _seed_video(db, "Other Video", drive_file_id="ov1")
    resp = client.get(f"/api/v1/videos?category_id={cat.id}")
    data = resp.json()
    assert all(v["category_id"] == cat.id for v in data["items"])
    assert data["total"] == 1


def test_videos_pagination(client, db):
    for i in range(5):
        _seed_video(db, f"Vid {i}", drive_file_id=f"pagvid{i}")
    resp = client.get("/api/v1/videos?skip=0&limit=3")
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5
    assert data["skip"] == 0
    assert data["limit"] == 3


def test_videos_response_shape(client, db):
    _seed_video(db, "Shape Test", drive_file_id="shape1")
    data = client.get("/api/v1/videos").json()
    v = data["items"][0]
    for field in ("id", "drive_file_id", "title", "is_active", "created_at"):
        assert field in v


# ── detail ─────────────────────────────────────────────────────────────────────

def test_get_video_by_id(client, db):
    vid = _seed_video(db, "Detail Vid", drive_file_id="detail1")
    resp = client.get(f"/api/v1/videos/{vid.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == vid.id


def test_get_inactive_video_returns_404(client, db):
    vid = _seed_video(db, "Hidden Vid", drive_file_id="hidden1", is_active=False)
    resp = client.get(f"/api/v1/videos/{vid.id}")
    assert resp.status_code == 404


def test_get_nonexistent_video_returns_404(client):
    resp = client.get("/api/v1/videos/99999")
    assert resp.status_code == 404
