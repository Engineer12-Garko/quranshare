from fastapi import APIRouter
from sqlalchemy import text

from app.database import SessionLocal

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    """
    Liveness + basic DB connectivity check.
    Returns 200 when the app is running and can reach PostgreSQL.
    Returns 503 when the database is unreachable.
    """
    from fastapi import HTTPException
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}")

    return {"status": "ok", "database": db_status}
