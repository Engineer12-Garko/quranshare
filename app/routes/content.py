from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.quran import VerseOfDayResponse
from app.services.quran_foundation import QuranFoundationError, get_verse_of_day

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/verse-of-day", response_model=VerseOfDayResponse)
def verse_of_day(response: Response, requested_date: date | None = Query(default=None, alias="date")):
    """Return today's stable Quran Foundation verse and translation."""
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
