from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests

from app.config import settings
from app.services import quran_foundation as qf


@pytest.fixture(autouse=True)
def reset_qf_cache(monkeypatch):
    qf._token_value = None
    qf._token_expires_at = 0
    qf._daily_cache.clear()
    qf._chapters_cache = None
    monkeypatch.setattr(settings, "qf_client_id", "test-client")
    monkeypatch.setattr(settings, "qf_client_secret", "test-secret")
    monkeypatch.setattr(settings, "qf_env", "prelive")
    monkeypatch.setattr(settings, "qf_translation_id", "131")
    yield
    qf._token_value = None
    qf._token_expires_at = 0
    qf._daily_cache.clear()
    qf._chapters_cache = None


def response(status=200, payload=None, headers=None):
    result = Mock()
    result.status_code = status
    result.headers = headers or {}
    result.json.return_value = payload or {}
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    return result


def test_token_uses_documented_oauth_scope_and_is_cached():
    token_response = response(payload={"access_token": "token-1", "expires_in": 3600})
    with patch.object(qf.requests, "post", return_value=token_response) as post:
        assert qf._get_access_token() == "token-1"
        assert qf._get_access_token() == "token-1"

    assert post.call_count == 1
    assert post.call_args.kwargs["data"] == {"grant_type": "client_credentials", "scope": "content"}
    assert post.call_args.args[0] == "https://prelive-oauth2.quran.foundation/oauth2/token"


def test_expired_token_is_renewed():
    qf._token_value = "expired-token"
    qf._token_expires_at = 0
    with patch.object(qf.requests, "post", return_value=response(payload={"access_token": "new-token"})) as post:
        assert qf._get_access_token() == "new-token"
    assert post.call_count == 1


def test_verse_response_maps_documented_fields_and_retries_one_401():
    token_responses = [
        response(payload={"access_token": "token-1", "expires_in": 3600}),
        response(payload={"access_token": "token-2", "expires_in": 3600}),
    ]
    verse_response = response(payload={"verse": {
        "verse_key": "2:152",
        "text_uthmani": "فَاذْكُرُونِي أَذْكُرْكُمْ",
        "translations": [{"resource_id": 131, "resource_name": "Clear Quran", "text": "Remember Me; I will remember you."}],
    }})
    with patch.object(qf.requests, "post", side_effect=token_responses) as post, \
         patch.object(qf.requests, "get", side_effect=[response(401), verse_response]) as get:
        result = qf._fetch_verse("2:152")

    assert result["verse_key"] == "2:152"
    assert result["arabic"] == "فَاذْكُرُونِي أَذْكُرْكُمْ"
    assert result["translation"] == "Remember Me; I will remember you."
    assert result["translation_source"] == "Clear Quran"
    assert post.call_count == 2
    assert get.call_count == 2
    assert get.call_args.kwargs["headers"] == {"x-auth-token": "token-2", "x-client-id": "test-client"}
    assert get.call_args.kwargs["params"]["translations"] == "131"


def test_transient_timeout_is_retried_once_then_reported(monkeypatch):
    monkeypatch.setattr(qf.time, "sleep", lambda _: None)
    with patch.object(qf.requests, "post", return_value=response(payload={"access_token": "token"})), \
         patch.object(qf.requests, "get", side_effect=requests.Timeout("timeout")) as get:
        with pytest.raises(qf.QuranFoundationError):
            qf._fetch_verse("20:114")
    assert get.call_count == 2


@pytest.mark.parametrize("status_code", [429, 503])
def test_rate_limit_and_server_errors_get_one_bounded_retry(monkeypatch, status_code):
    monkeypatch.setattr(qf.time, "sleep", lambda _: None)
    qf._token_value = "cached-token"
    qf._token_expires_at = qf.time.monotonic() + 3600
    valid_verse = response(payload={"verse": {
        "verse_key": "1:1",
        "text_uthmani": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "translations": [{"resource_id": 131, "resource_name": "Clear Quran", "text": "In the name of Allah."}],
    }})
    with patch.object(qf.requests, "get", side_effect=[response(status_code, headers={"Retry-After": "0"}), valid_verse]) as get:
        assert qf._fetch_verse("1:1")["verse_key"] == "1:1"
    assert get.call_count == 2


def test_forbidden_response_is_not_retried():
    qf._token_value = "cached-token"
    qf._token_expires_at = qf.time.monotonic() + 3600
    with patch.object(qf.requests, "get", return_value=response(403)) as get:
        with pytest.raises(qf.QuranFoundationError):
            qf._fetch_verse("1:1")
    get.assert_called_once()


def test_daily_verse_is_stable_and_cached_for_the_date():
    chapters = [{"id": 1, "name_simple": "Al-Fatihah", "name_arabic": "الفاتحة", "verses_count": 1}]
    verses = [{"verse_key": "1:1", "chapter_id": 1, "verse_number": 1, "arabic": "Arabic", "translation": "Ease follows hardship."}]
    with patch.object(qf, "get_chapters", return_value=chapters), \
         patch.object(qf, "get_chapter_verses", return_value={"verses": verses}) as fetch:
        first = qf.get_verse_of_day(date(2026, 10, 17))
        second = qf.get_verse_of_day(date(2026, 10, 17))
    assert first == second
    assert first["date"] == "2026-10-17"
    fetch.assert_called_once()


def test_chapter_verses_maps_api_envelope_and_pagination():
    qf._chapters_cache = (qf.time.monotonic() + 3600, [{"id": 1, "name_simple": "Al-Fatihah", "name_arabic": "الفاتحة", "verses_count": 7, "translated_name": "The Opening"}])
    qf._token_value = "cached-token"
    qf._token_expires_at = qf.time.monotonic() + 3600
    payload = {"verses": [{"verse_key": "1:1", "chapter_id": 1, "verse_number": 1, "text_uthmani": "بِسْمِ اللَّهِ", "translations": [{"resource_id": 131, "resource_name": "Clear Quran", "text": "In the name of Allah."}]}], "pagination": {"current_page": 1, "next_page": 2, "total_pages": 2, "total_records": 7}}
    with patch.object(qf.requests, "get", return_value=response(payload=payload)) as get:
        result = qf.get_chapter_verses(1, page=1, per_page=5)
    assert result["verses"][0]["verse_key"] == "1:1"
    assert result["verses"][0]["chapter_name"] == "Al-Fatihah"
    assert result["pagination"]["next_page"] == 2
    assert get.call_args.kwargs["params"] == {"translations": "131", "fields": "text_uthmani", "translation_fields": "resource_name", "page": 1, "per_page": 5}


def test_pre_live_chapter_list_filters_to_available_content():
    qf._token_value = "cached-token"
    qf._token_expires_at = qf.time.monotonic() + 3600
    payload = {"chapters": [{"id": i, "name_simple": f"Surah {i}", "name_arabic": "سورة", "verses_count": 7, "translated_name": {"name": "Name"}} for i in (1, 2, 3)]}
    with patch.object(qf.requests, "get", return_value=response(payload=payload)):
        assert [chapter["id"] for chapter in qf.get_chapters()] == [1, 2]


def test_missing_configured_translation_is_not_silently_substituted():
    with pytest.raises(ValueError, match="configured translation"):
        qf._map_verse({"verse_key": "1:1", "text_uthmani": "Arabic", "translations": [{"resource_id": 85, "text": "Different translation"}]})
