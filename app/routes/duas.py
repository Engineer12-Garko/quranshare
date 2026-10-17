from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.dua import DuaResponse, DuaSummaryResponse
from app.services.opendua import OpenDuaError, get_collections, get_entry, search_entries

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


@router.get("", response_model=list[DuaSummaryResponse])
def dua_list(
    response: Response,
    search: str = Query(default="", max_length=100),
    category: str = Query(default="", max_length=120),
):
    try:
        result = search_entries(search, category)
    except OpenDuaError as exc:
        raise _dua_error(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=900, stale-while-revalidate=3600"
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
