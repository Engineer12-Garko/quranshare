from unittest.mock import patch

from app.services.quran_foundation import QuranFoundationError


def test_verse_of_day_returns_mapped_content_and_public_cache_header(client):
    expected = {
        "date": "2026-10-17",
        "verse_key": "94:6",
        "arabic": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "translation": "Indeed, with hardship comes ease.",
        "translation_source": "Clear Quran",
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
