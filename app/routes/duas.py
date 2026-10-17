from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.dua import DuaResponse, DuaSearchResponse
from app.services.opendua import OpenDuaError, get_collections, get_dua_of_day, get_entry, search_entries_page as search_entries

router = APIRouter(prefix="/duas", tags=["duas"])


def _dua_error(exc: OpenDuaError) -> HTTPException:
    if exc.status_code == 429:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The live Du'a provider is rate-limited. Please try again shortly.",
            headers={"Cache-Control": "no-store", "Retry-After": "60"},
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/collections")
def collections(response: Response):
    try:
        result = get_collections()
    except OpenDuaError as exc:
        raise _dua_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return result


@router.get("", response_model=DuaSearchResponse)
def dua_list(
    response: Response,
    search: str = Query(default="", max_length=100),
    category: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
):
    try:
        result = search_entries(search, category, page, limit)
    except OpenDuaError as exc:
        raise _dua_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=900, stale-while-revalidate=3600"
    return result


@router.get("/daily", response_model=DuaResponse)
def daily_dua(response: Response, requested_date: str | None = Query(default=None, alias="date")):
    try:
        from datetime import date
        day = date.fromisoformat(requested_date) if requested_date else None
        result = get_dua_of_day(day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OpenDuaError as exc:
        raise _dua_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=86400"
    return result


@router.get("/{entry_id}", response_model=DuaResponse)
def dua_detail(entry_id: str, response: Response):
    try:
        result = get_entry(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OpenDuaError as exc:
        raise _dua_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return result
