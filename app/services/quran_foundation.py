"""Small, server-side Quran Foundation Content API client."""
from __future__ import annotations

import logging
import threading
import time
from datetime import date
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

from app.config import settings

logger = logging.getLogger(__name__)

# Pre-live only includes Al-Fatihah and Al-Baqarah, so every deterministic
# selection must be available in both pre-live and production environments.
_VERSE_KEYS = ("1:1", "2:152", "2:255")
_TOKEN_EARLY_REFRESH_SECONDS = 60
_HTTP_TIMEOUT = (3.05, 8)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_token_lock = threading.Lock()
_token_value: str | None = None
_token_expires_at = 0.0
_daily_cache: dict[str, dict] = {}
_daily_cache_lock = threading.Lock()


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
        if (
            not force_refresh
            and _token_value
            and now < _token_expires_at - _TOKEN_EARLY_REFRESH_SECONDS
        ):
            return _token_value

        oauth_base, _ = _hosts()
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = requests.post(
                    f"{oauth_base}/oauth2/token",
                    auth=HTTPBasicAuth(settings.qf_client_id, settings.qf_client_secret),
                    data={"grant_type": "client_credentials", "scope": "content"},
                    timeout=_HTTP_TIMEOUT,
                )
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt == 0:
                    time.sleep(_retry_delay(response))
                    continue
                response.raise_for_status()
                payload = response.json()
                token = payload.get("access_token")
                if not token:
                    raise QuranFoundationError("Quran Foundation returned no access token.")
                expires_in = max(1, int(payload.get("expires_in", 3600)))
                _token_value = token
                _token_expires_at = time.monotonic() + expires_in
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

        _token_value = None
        _token_expires_at = 0.0
        logger.warning("Quran Foundation token request failed (%s).", type(last_error).__name__)
        raise QuranFoundationError("Unable to authenticate with Quran Foundation.") from last_error


def _is_transient_exception(exc: requests.RequestException) -> bool:
    return isinstance(exc, (requests.Timeout, requests.ConnectionError))


def _retry_delay(response: requests.Response) -> float:
    try:
        return min(max(float(response.headers.get("Retry-After", "0.15")), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.15


def _fetch_verse(verse_key: str) -> dict:
    global _token_value, _token_expires_at
    _, api_base = _hosts()
    url = f"{api_base}/content/api/v4/verses/by_key/{quote(verse_key, safe=':')}"
    params = {
        "translations": settings.qf_translation_id,
        "fields": "text_uthmani",
        "translation_fields": "resource_name",
    }

    for auth_attempt in range(2):
        token = _get_access_token(force_refresh=bool(auth_attempt))
        headers = {"x-auth-token": token, "x-client-id": settings.qf_client_id}
        for transient_attempt in range(2):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=_HTTP_TIMEOUT)
                if response.status_code == 401 and auth_attempt == 0:
                    with _token_lock:
                        _token_value = None
                        _token_expires_at = 0.0
                    break
                if response.status_code in _RETRYABLE_STATUS_CODES and transient_attempt == 0:
                    time.sleep(_retry_delay(response))
                    continue
                response.raise_for_status()
                return _map_verse_response(response.json(), verse_key)
            except requests.RequestException as exc:
                if transient_attempt == 0 and _is_transient_exception(exc):
                    time.sleep(0.15)
                    continue
                logger.warning("Quran Foundation verse request failed (%s).", type(exc).__name__)
                raise QuranFoundationError("Unable to load Quran verse content.") from exc
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                logger.warning("Quran Foundation verse response was invalid (%s).", type(exc).__name__)
                raise QuranFoundationError("Quran Foundation returned an invalid verse response.") from exc
        else:
            # No 401 refresh was requested; the transient loop failed.
            raise QuranFoundationError("Unable to load Quran verse content.")

    raise QuranFoundationError("Quran Foundation rejected the refreshed access token.")


def _map_verse_response(payload: dict, expected_key: str) -> dict:
    verse = payload["verse"]
    translations = verse.get("translations") or []
    translation = next(
        (item for item in translations if int(item.get("resource_id", -1)) == int(settings.qf_translation_id)),
        translations[0] if translations else None,
    )
    arabic = verse.get("text_uthmani")
    translated = translation.get("text") if translation else None
    if not arabic or not translated:
        raise ValueError("Missing verse text or translation")
    return {
        "verse_key": verse.get("verse_key") or expected_key,
        "arabic": arabic,
        "translation": translated,
        "translation_source": translation.get("resource_name"),
        "source": "Quran Foundation Content API",
    }


def get_verse_of_day(today: date | None = None) -> dict:
    """Return one deterministic verse per day; cache the public response for that day."""
    current_date = today or date.today()
    date_key = current_date.isoformat()
    with _daily_cache_lock:
        cached = _daily_cache.get(date_key)
        if cached:
            return dict(cached)

    verse_key = _VERSE_KEYS[current_date.toordinal() % len(_VERSE_KEYS)]
    verse = _fetch_verse(verse_key)
    verse["date"] = date_key
    with _daily_cache_lock:
        _daily_cache.clear()
        _daily_cache[date_key] = verse
    return dict(verse)
