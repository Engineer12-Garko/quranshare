from unittest.mock import patch

from app.services.quran_foundation import QuranFoundationError


def test_verse_of_day_returns_mapped_content_and_public_cache_header(client):
    expected = {
        "date": "2026-10-17",
        "verse_key": "94:6",
        "chapter_id": 94,
        "verse_number": 6,
        "chapter_name": "Ash-Sharh",
        "chapter_name_arabic": "الشرح",
        "arabic": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "translation": "Indeed, with hardship comes ease.",
        "translation_source": "Clear Quran",
        "translation_resource_id": 131,
        "juz_number": None,
        "hizb_number": None,
        "page_number": None,
        "ruku_number": None,
        "manzil_number": None,
        "source": "Quran Foundation Content API",
    }
    with patch("app.routes.content.get_verse_of_day", return_value=expected):
        response = client.get("/api/v1/content/verse-of-day")

    assert response.status_code == 200
    assert response.json() == expected
    assert "max-age=3600" in response.headers["cache-control"]


def test_verse_of_day_returns_graceful_503_when_upstream_is_unavailable(client):
    with patch("app.routes.content.get_verse_of_day", side_effect=QuranFoundationError("private detail")):
        response = client.get("/api/v1/content/verse-of-day")

    assert response.status_code == 503
    assert response.json()["detail"] == "Quran verse content is temporarily unavailable."
    assert response.headers["cache-control"] == "no-store"


def test_chapter_verses_endpoint_validates_page_size_and_uses_public_cache(client):
    from app.routes import content

    expected = {"chapter": {"id": 1, "name_simple": "Al-Fatihah", "name_arabic": "الفاتحة", "name_complex": None, "translated_name": None, "verses_count": 7, "revelation_place": None}, "verses": [], "pagination": {"current_page": 1, "next_page": None, "total_pages": 1, "total_records": 7}}
    with patch.object(content, "get_chapter_verses", return_value=expected) as get:
        response = client.get("/api/v1/content/chapters/1/verses?page=1&per_page=50")
    assert response.status_code == 200
    assert "max-age=3600" in response.headers["cache-control"]
    get.assert_called_once_with(1, 1, 50)

    invalid = client.get("/api/v1/content/chapters/1/verses?per_page=51")
    assert invalid.status_code == 422


def test_verse_by_key_rejects_invalid_reference(client):
    response = client.get("/api/v1/content/verses/by-key/nope")
    assert response.status_code == 422
