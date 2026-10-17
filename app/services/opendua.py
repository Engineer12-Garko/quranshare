"""Public OpenDua API client."""
from __future__ import annotations

import logging
import threading
import time

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.opendua.org/v2"
COLLECTION_ID = "hisn-al-muslim"
_TIMEOUT = (3.05, 8)
_RETRYABLE = {429, 500, 502, 503, 504}
_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}


class OpenDuaError(Exception):
    """Raised when OpenDua cannot return valid content."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _request(path: str) -> dict:
    for attempt in range(2):
        try:
            response = requests.get(f"{BASE_URL}/{path.lstrip('/')}", timeout=_TIMEOUT)
            if response.status_code in _RETRYABLE and attempt == 0:
                time.sleep(0.15)
                continue
            if response.status_code == 429:
                raise OpenDuaError("Du'a provider rate limit reached.", 429)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("unexpected provider response")
            return payload
        except OpenDuaError:
            raise
        except requests.Timeout as exc:
            if attempt == 0:
                continue
            logger.warning("OpenDua request timed out.")
            raise OpenDuaError("Du'a content took too long to respond.") from exc
        except requests.RequestException as exc:
            logger.warning("OpenDua request failed (%s).", type(exc).__name__)
            raise OpenDuaError("Unable to load live Du'a content.") from exc
        except (TypeError, ValueError) as exc:
            logger.warning("OpenDua response was invalid (%s).", type(exc).__name__)
            raise OpenDuaError("The live Du'a provider returned invalid data.") from exc
    raise OpenDuaError("Unable to load live Du'a content.")


def _cached(key: str, loader, ttl: int):
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry[0] > now:
            return entry[1]
    value = loader()
    with _cache_lock:
        _cache[key] = (now + ttl, value)
    return value


def get_collections() -> list[dict]:
    def load():
        items = _request("collections").get("items")
        if not isinstance(items, list):
            raise OpenDuaError("The live Du'a provider returned invalid collections.")
        return [dict(item) for item in items]

    return [dict(item) for item in _cached("collections", load, 3600)]


def get_chapters() -> list[dict]:
    def load():
        items = _request(f"collections/{COLLECTION_ID}/chapters").get("items")
        if not isinstance(items, list):
            raise OpenDuaError("The live Du'a provider returned invalid chapters.")
        return [dict(item) for item in items]

    return [dict(item) for item in _cached("chapters", load, 3600)]


def get_entry_summaries() -> list[dict]:
    def load():
        items = _request(f"collections/{COLLECTION_ID}/entries").get("items")
        if not isinstance(items, list):
            raise OpenDuaError("The live Du'a provider returned invalid entries.")
        return [dict(item) for item in items]

    return [dict(item) for item in _cached("entries", load, 900)]


def _map_entry(entry: dict, chapter_title: str | None = None) -> dict:
    variations = entry.get("variations") or []
    first = variations[0] if variations and isinstance(variations[0], dict) else {}
    steps = first.get("steps") or []
    recitation = next((step for step in steps if isinstance(step, dict) and step.get("type") == "recitation"), {})
    items = recitation.get("items") or []
    dua = next((item.get("dua") for item in items if isinstance(item, dict) and isinstance(item.get("dua"), dict)), {})
    recordings = recitation.get("recordings") or []
    recording = next((item for item in recordings if isinstance(item, dict) and item.get("url")), None)
    return {
        "id": str(entry["id"]),
        "title": str(entry.get("title") or entry["id"]),
        "category": chapter_title or "OpenDua",
        "arabic": dua.get("arabic", ""),
        "transliteration": dua.get("transliteration"),
        "translation": dua.get("translation", ""),
        "source_reference": entry.get("sourceReference"),
        "references": dua.get("references") or entry.get("references") or [],
        "audio_url": recording.get("url") if recording else None,
        "source": "OpenDua",
        "source_url": "https://opendua.org",
    }


def get_entry(entry_id: str) -> dict:
    if not entry_id or "/" in entry_id:
        raise ValueError("entry_id is invalid")
    chapters = {item["id"]: item.get("title") for item in get_chapters()}
    try:
        entry = _request(f"entries/{entry_id}")
        if not entry.get("id") or not entry.get("variations"):
            raise ValueError("missing entry content")
        return _map_entry(entry, chapters.get(entry.get("chapterId")))
    except (KeyError, TypeError, ValueError) as exc:
        raise OpenDuaError("The live Du'a provider returned invalid entry content.") from exc


def search_entries(query: str = "", category: str = "") -> list[dict]:
    chapters = {item["id"]: item for item in get_chapters()}
    summaries = get_entry_summaries()
    query_lower = query.strip().casefold()
    category_lower = category.strip().casefold()
    matching = []
    for item in summaries:
        chapter = chapters.get(item.get("chapterId"))
        title = str(item.get("title") or "")
        chapter_title = str((chapter or {}).get("title") or "OpenDua")
        if category_lower and category_lower not in chapter_title.casefold():
            continue
        if query_lower and query_lower not in f"{title} {chapter_title}".casefold():
            continue
        matching.append({
            "id": str(item["id"]),
            "title": title,
            "category": chapter_title,
            "source_reference": item.get("sourceReference"),
            "source": "OpenDua",
        })
    return matching
