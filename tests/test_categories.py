"""
Tests for GET /api/v1/categories.
"""
from app.models.category import Category


def _seed_category(db, name, is_active=True):
    cat = Category(name=name, description=f"Desc for {name}", is_active=is_active)
    db.add(cat)
    db.flush()
    return cat


def test_categories_returns_empty_list(client):
    resp = client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert resp.json() == []


def test_categories_returns_active_only(client, db):
    _seed_category(db, "Active Cat")
    _seed_category(db, "Inactive Cat", is_active=False)
    resp = client.get("/api/v1/categories")
    assert resp.status_code == 200
    data = resp.json()
    names = [c["name"] for c in data]
    assert "Active Cat" in names
    assert "Inactive Cat" not in names


def test_categories_ordered_by_name(client, db):
    _seed_category(db, "Zakat")
    _seed_category(db, "Iman")
    _seed_category(db, "Adab")
    resp = client.get("/api/v1/categories")
    names = [c["name"] for c in resp.json()]
    assert names == sorted(names)


def test_category_response_shape(client, db):
    _seed_category(db, "Tawhid")
    data = client.get("/api/v1/categories").json()
    assert len(data) >= 1
    cat = data[0]
    assert "id" in cat
    assert "name" in cat
    assert "description" in cat
    assert "is_active" in cat
    assert "created_at" in cat
