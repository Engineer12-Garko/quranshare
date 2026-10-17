"""Server-side Quran Foundation Content API client."""
from __future__ import annotations

import logging
import re
import threading
import time
from datetime import date
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

from app.config import settings

logger = logging.getLogger(__name__)
_TOKEN_EARLY_REFRESH_SECONDS = 60
_HTTP_TIMEOUT = (3.05, 8)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_token_lock = threading.Lock()
_token_value: str | None = None
_token_expires_at = 0.0
_cache_lock = threading.Lock()
_chapters_cache: tuple[float, list[dict]] | None = None
_daily_cache: dict[str, dict] = {}


class QuranFoundationError(Exception):
    """Raised for configuration, transport, or response errors."""


def _hosts() -> tuple[str, str]:
    if settings.qf_env == "prelive":
        return "https://prelive-oauth2.quran.foundation", "https://apis-prelive.quran.foundation"
    return "https://oauth2.quran.foundation", "https://apis.quran.foundation"


def _get_access_token(force_refresh: bool = False) -> str:
    global _token_value, _token_expires_at
    if not settings.qf_client_id or not settings.qf_client_secret:
        raise QuranFoundationError("Quran Foundation API credentials are not configured.")
    with _token_lock:
        now = time.monotonic()
        if not force_refresh and _token_value and now < _token_expires_at - _TOKEN_EARLY_REFRESH_SECONDS:
            return _token_value
        oauth_base, _ = _hosts()
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = requests.post(
                    f"{oauth_base}/oauth2/token",
                    auth=HTTPBasicAuth(settings.qf_client_id, settings.qf_client_secret),
                    data={"grant_type": "client_credentials", "scope": "content"}, timeout=_HTTP_TIMEOUT,
                )
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt == 0:
                    time.sleep(_retry_delay(response))
                    continue
                response.raise_for_status()
                payload = response.json()
                token = payload.get("access_token")
                if not token:
                    raise ValueError("missing access token")
                _token_value = token
                _token_expires_at = time.monotonic() + max(1, int(payload.get("expires_in", 3600)))
                return token
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 0 and _is_transient_exception(exc):
                    time.sleep(0.15)
                    continue
                break
            except (ValueError, TypeError) as exc:
                last_error = exc
                break
        _token_value, _token_expires_at = None, 0.0
        logger.warning("Quran Foundation token request failed (%s).", type(last_error).__name__)
        raise QuranFoundationError("Unable to authenticate with Quran Foundation.") from last_error


def _is_transient_exception(exc: requests.RequestException) -> bool:
    return isinstance(exc, (requests.Timeout, requests.ConnectionError))


def _retry_delay(response: requests.Response) -> float:
    try:
        return min(max(float(response.headers.get("Retry-After", "0.15")), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.15


def _get_json(path: str, params: dict | None = None) -> dict:
    """Make one authenticated Content API request with bounded retry/401 refresh."""
    global _token_value, _token_expires_at
    _, api_base = _hosts()
    url = f"{api_base}/content/api/v4/{path.lstrip('/')}"
    for auth_attempt in range(2):
        token = _get_access_token(force_refresh=bool(auth_attempt))
        headers = {"x-auth-token": token, "x-client-id": settings.qf_client_id}
        for transient_attempt in range(2):
            try:
                response = requests.get(url, headers=headers, params=params or {}, timeout=_HTTP_TIMEOUT)
                if response.status_code == 401 and auth_attempt == 0:
                    with _token_lock:
                        _token_value, _token_expires_at = None, 0.0
                    break
                if response.status_code in _RETRYABLE_STATUS_CODES and transient_attempt == 0:
                    time.sleep(_retry_delay(response))
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("response is not an object")
                return payload
            except requests.RequestException as exc:
                if transient_attempt == 0 and _is_transient_exception(exc):
                    time.sleep(0.15)
                    continue
                logger.warning("Quran Foundation request failed (%s).", type(exc).__name__)
                raise QuranFoundationError("Unable to load Quran content.") from exc
            except (ValueError, TypeError) as exc:
                logger.warning("Quran Foundation response was invalid (%s).", type(exc).__name__)
                raise QuranFoundationError("Quran Foundation returned an invalid response.") from exc
        else:
            raise QuranFoundationError("Unable to load Quran content.")
    raise QuranFoundationError("Quran Foundation rejected the refreshed access token.")


def _translation(verse: dict) -> dict:
    translations = verse.get("translations") or []
    selected = next(
        (item for item in translations if str(item.get("resource_id")) == str(settings.qf_translation_id)),
        None,
    )
    if not selected or not selected.get("text"):
        raise ValueError("Quran Foundation response is missing the configured translation")
    return selected


def _map_verse(verse: dict, chapter: dict | None = None) -> dict:
    translation = _translation(verse)
    key = verse.get("verse_key")
    if not key or not verse.get("text_uthmani"):
        raise ValueError("Quran Foundation response is missing verse fields")
    try:
        chapter_id, verse_number = (int(part) for part in key.split(":", 1))
    except (ValueError, AttributeError):
        raise ValueError("Quran Foundation returned an invalid verse key")
    return {
        "verse_key": key,
        "chapter_id": verse.get("chapter_id", chapter_id),
        "verse_number": verse.get("verse_number", verse_number),
        "chapter_name": (chapter or {}).get("name_simple"),
        "chapter_name_arabic": (chapter or {}).get("name_arabic"),
        "arabic": verse["text_uthmani"],
        "translation": translation["text"],
        "translation_source": translation.get("resource_name"),
        "translation_resource_id": translation.get("resource_id"),
        "juz_number": verse.get("juz_number"),
        "hizb_number": verse.get("hizb_number"),
        "page_number": verse.get("page_number"),
        "ruku_number": verse.get("ruku_number"),
        "manzil_number": verse.get("manzil_number"),
        "source": "Quran Foundation Content API",
    }


def _map_chapter(chapter: dict) -> dict:
    required = ("id", "name_simple", "name_arabic", "verses_count")
    if any(field not in chapter for field in required):
        raise ValueError("Quran Foundation returned incomplete chapter metadata")
    return {
        "id": int(chapter["id"]), "name_simple": chapter["name_simple"],
        "name_arabic": chapter["name_arabic"], "name_complex": chapter.get("name_complex"),
        "translated_name": (chapter.get("translated_name") or {}).get("name"),
        "verses_count": int(chapter["verses_count"]),
        "revelation_place": chapter.get("revelation_place"),
    }


def get_chapters() -> list[dict]:
    global _chapters_cache
    with _cache_lock:
        if _chapters_cache and _chapters_cache[0] > time.monotonic():
            return [dict(chapter) for chapter in _chapters_cache[1]]
    try:
        data = _get_json("chapters", {"language": "en"})["chapters"]
        chapters = [_map_chapter(chapter) for chapter in data]
        if not chapters:
            raise ValueError("empty chapter list")
        # Prelive exposes only Al-Fatihah and Al-Baqarah.
        if settings.qf_env == "prelive":
            chapters = [chapter for chapter in chapters if chapter["id"] in (1, 2)]
        with _cache_lock:
            _chapters_cache = (time.monotonic() + 3600, chapters)
        return [dict(chapter) for chapter in chapters]
    except (KeyError, TypeError, ValueError) as exc:
        raise QuranFoundationError("Quran Foundation returned invalid chapter metadata.") from exc


def _chapter_by_id(chapter_id: int) -> dict:
    chapter = next((item for item in get_chapters() if item["id"] == chapter_id), None)
    if not chapter:
        raise QuranFoundationError("This chapter is not available in the configured Quran Foundation environment.")
    return chapter


def get_chapter_verses(chapter_number: int, page: int = 1, per_page: int = 50) -> dict:
    if not 1 <= chapter_number <= 114:
        raise ValueError("chapter_number must be between 1 and 114")
    if page < 1 or not 1 <= per_page <= 50:
        raise ValueError("page must be positive and per_page must be between 1 and 50")
    chapter = _chapter_by_id(chapter_number)
    payload = _get_json(f"verses/by_chapter/{chapter_number}", {
        "translations": settings.qf_translation_id, "fields": "text_uthmani",
        "translation_fields": "resource_name", "page": page, "per_page": per_page,
    })
    try:
        verses = [_map_verse(item, chapter) for item in payload["verses"]]
        pagination = payload["pagination"]
        if not isinstance(pagination, dict):
            raise ValueError("missing pagination")
        return {"chapter": chapter, "verses": verses, "pagination": {
            "current_page": pagination["current_page"], "next_page": pagination.get("next_page"),
            "total_pages": pagination["total_pages"], "total_records": pagination["total_records"],
        }}
    except (KeyError, TypeError, ValueError) as exc:
        raise QuranFoundationError("Quran Foundation returned invalid chapter verses.") from exc


def get_verse_by_key(verse_key: str) -> dict:
    if not re.fullmatch(r"\d{1,3}:\d{1,3}", verse_key):
        raise ValueError("verse_key must use the chapter:verse format")
    chapter_id, verse_number = (int(part) for part in verse_key.split(":"))
    chapter = _chapter_by_id(chapter_id)
    if not 1 <= verse_number <= chapter["verses_count"]:
        raise ValueError("verse number is outside the selected chapter")
    payload = _get_json(f"verses/by_key/{quote(verse_key, safe=':')}", {
        "translations": settings.qf_translation_id, "fields": "text_uthmani",
        "translation_fields": "resource_name",
    })
    try:
        return _map_verse(payload["verse"], chapter)
    except (KeyError, TypeError, ValueError) as exc:
        raise QuranFoundationError("Quran Foundation returned invalid verse content.") from exc


def _fetch_verse(verse_key: str) -> dict:
    """Fetch a keyed verse (kept as a small service helper for callers/tests)."""
    if not re.fullmatch(r"\d{1,3}:\d{1,3}", verse_key):
        raise ValueError("verse_key must use the chapter:verse format")
    payload = _get_json(f"verses/by_key/{quote(verse_key, safe=':')}", {
        "translations": settings.qf_translation_id, "fields": "text_uthmani",
        "translation_fields": "resource_name",
    })
    try:
        return _map_verse(payload["verse"])
    except (KeyError, TypeError, ValueError) as exc:
        raise QuranFoundationError("Quran Foundation returned invalid verse content.") from exc


def get_verse_of_day(today: date | None = None) -> dict:
    """Pick a stable verse from configured chapter metadata, using only available content."""
    current_date = today or date.today()
    key = current_date.isoformat()
    with _cache_lock:
        if key in _daily_cache:
            return dict(_daily_cache[key])
    chapters = get_chapters()
    total = sum(chapter["verses_count"] for chapter in chapters)
    if not total:
        raise QuranFoundationError("No verse content is available in the configured environment.")
    remaining = current_date.toordinal() % total
    selected = None
    verse_number = 0
    for chapter in chapters:
        if remaining < chapter["verses_count"]:
            selected = chapter
            verse_number = remaining + 1
            break
        remaining -= chapter["verses_count"]
    if selected is None:
        raise QuranFoundationError("Quran Foundation returned invalid chapter verse counts.")
    page = (verse_number - 1) // 50 + 1
    result = get_chapter_verses(selected["id"], page, 50)
    verse = next((item for item in result["verses"] if item["verse_number"] == verse_number), None)
    if verse is None:
        raise QuranFoundationError("The selected daily verse was not returned by Quran Foundation.")
    verse["date"] = key
    with _cache_lock:
        _daily_cache.clear()
        _daily_cache[key] = verse
    return dict(verse)
