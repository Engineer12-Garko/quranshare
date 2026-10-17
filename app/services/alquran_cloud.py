"""Public AlQuran Cloud client used by the live Quran reader."""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime, timezone

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.alquran.cloud/v1"
ARABIC_EDITION = "quran-uthmani"
TRANSLATION_EDITION = "en.sahih"
AUDIO_EDITION = "ar.alafasy"
_TIMEOUT = (3.05, 8)
_RETRYABLE = {429, 500, 502, 503, 504}
_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}


class AlQuranCloudError(Exception):
    """Raised when the public Quran provider cannot return valid content."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _request(path: str) -> dict:
    url = f"{BASE_URL}/{path.lstrip('/')}"
    for attempt in range(2):
        try:
            response = requests.get(url, timeout=_TIMEOUT)
            if response.status_code in _RETRYABLE and attempt == 0:
                time.sleep(0.15)
                continue
            if response.status_code == 429:
                raise AlQuranCloudError("Quran provider rate limit reached.", 429)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("code") != 200:
                raise ValueError("unexpected provider response")
            return payload
        except AlQuranCloudError:
            raise
        except requests.Timeout as exc:
            if attempt == 0:
                continue
            logger.warning("AlQuran Cloud request timed out.")
            raise AlQuranCloudError("Quran content took too long to respond.") from exc
        except requests.RequestException as exc:
            logger.warning("AlQuran Cloud request failed (%s).", type(exc).__name__)
            raise AlQuranCloudError("Unable to load live Quran content.") from exc
        except (TypeError, ValueError) as exc:
            logger.warning("AlQuran Cloud response was invalid (%s).", type(exc).__name__)
            raise AlQuranCloudError("The live Quran provider returned invalid data.") from exc
    raise AlQuranCloudError("Unable to load live Quran content.")


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


def _surah_metadata(item: dict) -> dict:
    required = ("number", "name", "englishName", "englishNameTranslation", "numberOfAyahs", "revelationType")
    if any(key not in item for key in required):
        raise ValueError("missing surah metadata")
    return {
        "id": int(item["number"]),
        "name_arabic": str(item["name"]),
        "name_simple": str(item["englishName"]),
        "translated_name": str(item["englishNameTranslation"]),
        "verses_count": int(item["numberOfAyahs"]),
        "revelation_place": str(item["revelationType"]),
    }


def get_surahs() -> list[dict]:
    def load():
        data = _request("surah").get("data")
        if not isinstance(data, list) or len(data) != 114:
            raise AlQuranCloudError("The live Quran provider returned an incomplete surah list.")
        try:
            return [_surah_metadata(item) for item in data]
        except (KeyError, TypeError, ValueError) as exc:
            raise AlQuranCloudError("The live Quran provider returned invalid surah metadata.") from exc

    return [dict(item) for item in _cached("surahs", load, 3600)]


def get_surah(number: int) -> dict:
    if not 1 <= number <= 114:
        raise ValueError("surah number must be between 1 and 114")

    def load():
        try:
            arabic = _request(f"surah/{number}/{ARABIC_EDITION}")["data"]
            translation = _request(f"surah/{number}/{TRANSLATION_EDITION}")["data"]
            metadata = _surah_metadata(arabic)
            arabic_ayahs = arabic["ayahs"]
            translation_ayahs = translation["ayahs"]
            if not all(isinstance(items, list) for items in (arabic_ayahs, translation_ayahs)):
                raise ValueError("missing ayahs")
            try:
                audio = _request(f"surah/{number}/{AUDIO_EDITION}")["data"]
                audio_ayahs = audio["ayahs"]
                if not isinstance(audio_ayahs, list) or len(audio_ayahs) != len(arabic_ayahs):
                    raise ValueError("audio ayah count differs")
            except (AlQuranCloudError, KeyError, TypeError, ValueError) as exc:
                logger.warning("AlQuran Cloud audio was unavailable (%s).", type(exc).__name__)
                audio_ayahs = [{} for _ in arabic_ayahs]
            if len(arabic_ayahs) != len(translation_ayahs):
                raise ValueError("edition ayah counts differ")
            verses = []
            for arabic_ayah, translation_ayah, audio_ayah in zip(
                arabic_ayahs, translation_ayahs, audio_ayahs, strict=True
            ):
                number_in_surah = int(arabic_ayah["numberInSurah"])
                if number_in_surah != int(translation_ayah["numberInSurah"]):
                    raise ValueError("edition verse references differ")
                verses.append({
                    "verse_key": f"{number}:{number_in_surah}",
                    "chapter_id": number,
                    "verse_number": number_in_surah,
                    "chapter_name": metadata["name_simple"],
                    "chapter_name_arabic": metadata["name_arabic"],
                    "arabic": str(arabic_ayah["text"]).strip(),
                    "translation": str(translation_ayah["text"]).strip(),
                    "translation_source": TRANSLATION_EDITION,
                    "translation_resource_id": TRANSLATION_EDITION,
                    "juz_number": arabic_ayah.get("juz"),
                    "page_number": arabic_ayah.get("page"),
                    "audio_url": audio_ayah.get("audio"),
                    "source": "AlQuran Cloud API",
                })
            return {"chapter": metadata, "verses": verses, "translation_edition": TRANSLATION_EDITION}
        except (KeyError, TypeError, ValueError) as exc:
            raise AlQuranCloudError("The live Quran provider returned invalid surah content.") from exc

    return dict(_cached(f"surah:{number}", load, 3600))


def get_verse_of_day(day: date | None = None) -> dict:
    """Select one real verse deterministically from the UTC calendar day."""
    daily_date = day or datetime.now(timezone.utc).date()
    key = f"daily-verse:{daily_date.isoformat()}"

    def load():
        surahs = sorted(get_surahs(), key=lambda item: item["id"])
        total = sum(item["verses_count"] for item in surahs)
        if total <= 0:
            raise AlQuranCloudError("The live Quran provider returned no verses.")
        offset = daily_date.toordinal() % total
        selected = None
        verse_number = 0
        for item in surahs:
            if offset < item["verses_count"]:
                selected = item
                verse_number = offset + 1
                break
            offset -= item["verses_count"]
        if selected is None:
            raise AlQuranCloudError("The live Quran provider returned invalid verse counts.")
        result = get_surah(selected["id"])
        verse = next(
            (item for item in result["verses"] if item["verse_number"] == verse_number),
            None,
        )
        if verse is None:
            raise AlQuranCloudError("The selected daily verse was not returned by the provider.")
        verse = dict(verse)
        verse["date"] = daily_date.isoformat()
        return verse

    return dict(_cached(key, load, 86400))
