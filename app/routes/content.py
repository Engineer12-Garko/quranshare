from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from app.schemas.quran import (
    ChapterResponse, ChapterVersesResponse, LiveChapterVersesResponse,
    VerseOfDayResponse, VerseResponse, LiveVerseResponse,
)
from app.services.alquran_cloud import AlQuranCloudError, get_surahs, get_surah, get_verse_of_day as get_live_verse_of_day
from app.services.quran_foundation import (
    QuranFoundationError, get_chapter_verses, get_chapters, get_verse_by_key, get_verse_of_day,
)

router = APIRouter(prefix="/content", tags=["content"])


def _service_error(exc: QuranFoundationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Quran content is temporarily unavailable.", headers={"Cache-Control": "no-store"})


@router.get("/chapters", response_model=list[ChapterResponse])
def chapters(response: Response):
    try:
        result = get_chapters()
    except QuranFoundationError as exc:
        raise _service_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return result


@router.get("/chapters/{chapter_number}/verses", response_model=ChapterVersesResponse)
def chapter_verses(
    response: Response,
    chapter_number: int = Path(ge=1, le=114),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=50),
):
    try:
        result = get_chapter_verses(chapter_number, page, per_page)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QuranFoundationError as exc:
        raise _service_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return result


@router.get("/verses/by-key/{verse_key}", response_model=VerseResponse)
def verse_by_key(verse_key: str, response: Response):
    try:
        verse = get_verse_by_key(verse_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QuranFoundationError as exc:
        raise _service_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
    return verse


@router.get("/verse-of-day", response_model=VerseOfDayResponse)
def verse_of_day(response: Response, requested_date: date | None = Query(default=None, alias="date")):
    try:
        verse = get_verse_of_day(requested_date)
    except QuranFoundationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quran verse content is temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from exc
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return verse


def _live_quran_error(exc: AlQuranCloudError) -> HTTPException:
    if exc.status_code == 429:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The live Quran provider is rate-limited. Please try again shortly.",
            headers={"Cache-Control": "no-store", "Retry-After": "60"},
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/quran/surahs", response_model=list[ChapterResponse])
def live_surahs(response: Response):
    try:
        result = get_surahs()
    except AlQuranCloudError as exc:
        raise _live_quran_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return result


@router.get("/quran/surahs/{surah_number}", response_model=LiveChapterVersesResponse)
def live_surah(
    response: Response,
    surah_number: int = Path(ge=1, le=114),
):
    try:
        result = get_surah(surah_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AlQuranCloudError as exc:
        raise _live_quran_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return result


@router.get("/quran/verse-of-day", response_model=LiveVerseResponse)
def live_verse_of_day(response: Response, requested_date: date | None = Query(default=None, alias="date")):
    try:
        result = get_live_verse_of_day(requested_date)
    except AlQuranCloudError as exc:
        raise _live_quran_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=86400"
    return result
