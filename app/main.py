from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.categories import router as categories_router
from app.routes.health import router as health_router
from app.routes.history import router as history_router
from app.routes.progress import router as progress_router
from app.routes.reminder import router as reminder_router
from app.routes.users import router as users_router
from app.routes.videos import router as videos_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="QuranFlow API",
    version="1.0.0",
    description="Curated Quranic reminder video library with WhatsApp sharing.",
    docs_url="/api/docs" if settings.app_env != "production" else None,
    redoc_url="/api/redoc" if settings.app_env != "production" else None,
    openapi_url="/api/openapi.json" if settings.app_env != "production" else None,
)

# CORS
if settings.app_env == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health_router,     prefix="/api/v1")
app.include_router(auth_router,       prefix="/api/v1")
app.include_router(users_router,      prefix="/api/v1")
app.include_router(videos_router,     prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(reminder_router,   prefix="/api/v1")
app.include_router(history_router,    prefix="/api/v1")
app.include_router(progress_router,   prefix="/api/v1")
app.include_router(admin_router,      prefix="/api/v1")

# ── Static files & SPA catch-all ───────────────────────────────────────────────
_static = BASE_DIR / "static"
_index  = BASE_DIR / "templates" / "index.html"

if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_catch_all(full_path: str):
    """Serve index.html for all non-API routes so the SPA router handles them."""
    return FileResponse(str(_index))
