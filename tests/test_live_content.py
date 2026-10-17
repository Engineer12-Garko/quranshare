from unittest.mock import Mock, patch

import pytest
import requests

from app.services import alquran_cloud as aq
from app.services import opendua


def response(status=200, payload=None):
    result = Mock()
    result.status_code = status
    result.json.return_value = payload or {}
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    return result


def surah_payload(edition, ayahs):
    return {
        "code": 200,
        "status": "OK",
        "data": {
            "number": 1,
            "name": "سُورَةُ ٱلْفَاتِحَةِ",
            "englishName": "Al-Faatiha",
            "englishNameTranslation": "The Opening",
            "numberOfAyahs": len(ayahs),
            "revelationType": "Meccan",
            "ayahs": ayahs,
            "edition": {"identifier": edition},
        },
    }


@pytest.fixture(autouse=True)
def reset_provider_caches():
    aq._cache.clear()
    opendua._cache.clear()
    yield
    aq._cache.clear()
    opendua._cache.clear()


def test_alquran_returns_all_114_surahs():
    payload = {
        "code": 200,
        "status": "OK",
        "data": [
            {
                "number": number,
                "name": f"سورة {number}",
                "englishName": f"Surah {number}",
                "englishNameTranslation": f"Translation {number}",
                "numberOfAyahs": 1,
                "revelationType": "Meccan",
            }
            for number in range(1, 115)
        ],
    }
    with patch.object(aq.requests, "get", return_value=response(payload=payload)):
        surahs = aq.get_surahs()
    assert len(surahs) == 114
    assert surahs[-1]["id"] == 114


def test_alquran_maps_arabic_translation_and_audio():
    arabic = [{"numberInSurah": 1, "text": "Arabic", "juz": 1, "page": 1}]
    translation = [{"numberInSurah": 1, "text": "Translation"}]
    audio = [{"numberInSurah": 1, "text": "Arabic", "audio": "https://audio.example/1.mp3"}]
    with patch.object(aq.requests, "get", side_effect=[
        response(payload=surah_payload("quran-uthmani", arabic)),
        response(payload=surah_payload("en.sahih", translation)),
        response(payload=surah_payload("ar.alafasy", audio)),
    ]):
        result = aq.get_surah(1)
    assert result["translation_edition"] == "en.sahih"
    assert result["verses"][0]["arabic"] == "Arabic"
    assert result["verses"][0]["translation"] == "Translation"
    assert result["verses"][0]["audio_url"].endswith(".mp3")


def test_alquran_keeps_text_when_audio_is_unavailable():
    arabic = [{"numberInSurah": 1, "text": "Arabic"}]
    translation = [{"numberInSurah": 1, "text": "Translation"}]
    with patch.object(aq.requests, "get", side_effect=[
        response(payload=surah_payload("quran-uthmani", arabic)),
        response(payload=surah_payload("en.sahih", translation)),
        requests.Timeout("audio unavailable"),
        requests.Timeout("audio unavailable"),
    ]):
        result = aq.get_surah(1)
    assert result["verses"][0]["translation"] == "Translation"
    assert result["verses"][0]["audio_url"] is None


def test_alquran_daily_verse_is_stable_and_uses_utc_date():
    surahs = [
        {"id": 1, "name_simple": "One", "name_arabic": "١", "verses_count": 2},
        {"id": 2, "name_simple": "Two", "name_arabic": "٢", "verses_count": 2},
    ]
    with patch.object(aq, "get_surahs", return_value=surahs), \
         patch.object(aq, "get_surah", side_effect=[
             {"verses": [{"verse_number": 1, "verse_key": "1:1"}]},
             {"verses": [{"verse_number": 2, "verse_key": "1:2"}]},
         ]):
        first = aq.get_verse_of_day(__import__("datetime").date(2026, 10, 17))
        second = aq.get_verse_of_day(__import__("datetime").date(2026, 10, 17))
    assert first == second


def test_alquran_rejects_invalid_surah_identifier():
    with pytest.raises(ValueError):
        aq.get_surah(115)


def test_alquran_timeout_is_reported_without_leaking_provider_details(monkeypatch):
    monkeypatch.setattr(aq.time, "sleep", lambda _: None)
    with patch.object(aq.requests, "get", side_effect=requests.Timeout("private detail")):
        with pytest.raises(aq.AlQuranCloudError, match="too long"):
            aq.get_surahs()


def test_opendua_maps_entry_with_translation_reference_and_audio():
    payload = {
        "id": "entry-000001",
        "title": "Wake up",
        "chapterId": "chapter-000001",
        "sourceReference": "1",
        "variations": [{
            "steps": [{
                "type": "recitation",
                "items": [{"dua": {
                    "arabic": "عربي",
                    "transliteration": "Arabic",
                    "translation": "Translation",
                    "references": [{"source": "Hadith"}],
                }}],
                "recordings": [{"url": "https://audio.example/dua.mp3"}],
            }],
        }],
    }
    chapters = {"items": [{"id": "chapter-000001", "title": "Morning"}]}
    with patch.object(opendua.requests, "get", side_effect=[
        response(payload=chapters),
        response(payload=payload),
    ]):
        result = opendua.get_entry("entry-000001")
    assert result["arabic"] == "عربي"
    assert result["translation"] == "Translation"
    assert result["references"] == [{"source": "Hadith"}]
    assert result["audio_url"].endswith(".mp3")


def test_opendua_search_filters_real_entry_summaries():
    chapters = {"items": [{"id": "chapter-000001", "title": "Morning"}]}
    entries = {"items": [{"id": "entry-000001", "title": "Wake up", "chapterId": "chapter-000001", "sourceReference": "1"}]}
    with patch.object(opendua.requests, "get", side_effect=[
        response(payload=chapters),
        response(payload=entries),
    ]):
        result = opendua.search_entries("wake")
    assert result[0]["id"] == "entry-000001"


def test_opendua_normalizes_arabic_and_latin_search_text():
    assert opendua.normalize_search_text("  WÁKE   UP ") == "wake up"
    assert opendua.normalize_search_text("إِيمَان") == "ايمان"


def test_opendua_daily_dua_is_stable_and_uses_summary_ids():
    with patch.object(opendua, "get_entry_summaries", return_value=[
        {"id": "entry-000001"},
        {"id": "entry-000002"},
    ]), patch.object(opendua, "get_entry", side_effect=lambda entry_id: {"id": entry_id}):
        first = opendua.get_dua_of_day(__import__("datetime").date(2026, 10, 17))
        second = opendua.get_dua_of_day(__import__("datetime").date(2026, 10, 17))
    assert first == second


def test_live_quran_routes_return_normalized_data(client):
    from app.routes import content

    chapters = [{"id": 1, "name_simple": "Al-Fatihah", "name_arabic": "الفاتحة", "verses_count": 7}]
    chapter = {
        "chapter": chapters[0],
        "verses": [{
            "verse_key": "1:1",
            "chapter_id": 1,
            "verse_number": 1,
            "chapter_name": "Al-Fatihah",
            "chapter_name_arabic": "الفاتحة",
            "arabic": "Arabic",
            "translation": "Translation",
            "translation_source": "en.sahih",
            "translation_resource_id": "en.sahih",
            "source": "AlQuran Cloud API",
            "audio_url": "https://audio.example/1.mp3",
        }],
        "translation_edition": "en.sahih",
    }
    with patch.object(content, "get_surahs", return_value=chapters), \
         patch.object(content, "get_surah", return_value=chapter):
        assert client.get("/api/v1/content/quran/surahs").json()[0]["id"] == 1
        result = client.get("/api/v1/content/quran/surahs/1")
    assert result.status_code == 200
    assert result.json()["verses"][0]["audio_url"].endswith(".mp3")


def test_dua_routes_support_search_and_detail(client):
    from app.routes import duas

    summary = [{"id": "entry-000001", "title": "Wake up", "category": "Morning", "source_reference": "1", "source": "OpenDua"}]
    detail = {
        **summary[0],
        "arabic": "عربي",
        "transliteration": "Arabic",
        "translation": "Translation",
        "references": [],
        "audio_url": None,
        "source_url": "https://opendua.org",
    }
    with patch.object(duas, "search_entries", return_value={"items": summary, "total": 1, "page": 1, "limit": 20, "has_more": False}), \
         patch.object(duas, "get_entry", return_value=detail):
        result = client.get("/api/v1/duas?search=wake")
        entry = client.get("/api/v1/duas/entry-000001")
    assert result.status_code == 200
    assert result.json()["items"][0]["id"] == "entry-000001"
    assert entry.status_code == 200
    assert entry.json()["translation"] == "Translation"


def test_provider_rate_limit_routes_are_explicit(client):
    from app.routes import content, duas

    with patch.object(content, "get_surahs", side_effect=aq.AlQuranCloudError("limited", 429)), \
         patch.object(duas, "search_entries", side_effect=opendua.OpenDuaError("limited", 429)):
        assert client.get("/api/v1/content/quran/surahs").status_code == 429
        assert client.get("/api/v1/duas").status_code == 429


def test_daily_routes_return_provider_content(client):
    from app.routes import content, duas

    verse = {
        "verse_key": "1:1",
        "chapter_id": 1,
        "verse_number": 1,
        "chapter_name": "Al-Fatihah",
        "chapter_name_arabic": "الفاتحة",
        "arabic": "Arabic",
        "translation": "Translation",
        "translation_source": "en.sahih",
        "translation_resource_id": "en.sahih",
        "source": "AlQuran Cloud API",
        "audio_url": None,
        "date": "2026-10-17",
    }
    dua = {
        "id": "entry-000001",
        "title": "Wake up",
        "category": "Morning",
        "source_reference": "1",
        "source": "OpenDua",
        "arabic": "عربي",
        "transliteration": None,
        "translation": "Translation",
        "references": [],
        "audio_url": None,
        "source_url": "https://opendua.org",
    }
    with patch.object(content, "get_live_verse_of_day", return_value=verse), \
         patch.object(duas, "get_dua_of_day", return_value=dua):
        assert client.get("/api/v1/content/quran/verse-of-day?date=2026-10-17").status_code == 200
        assert client.get("/api/v1/duas/daily?date=2026-10-17").json()["id"] == "entry-000001"


@pytest.mark.parametrize("service, url", [
    (aq, "https://api.alquran.cloud/v1/surah"),
    (opendua, "https://api.opendua.org/v2/collections"),
])
def test_rate_limit_is_exposed_as_provider_error(service, url):
    with patch.object(service.requests, "get", return_value=response(429)):
        with pytest.raises(service.__dict__[next(name for name in service.__dict__ if name.endswith("Error"))]):
            if service is aq:
                service.get_surahs()
            else:
                service.get_collections()
