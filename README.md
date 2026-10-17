# QuranFlow

A curated Quranic/Islamic reminder video library with WhatsApp sharing.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic
- **Database:** PostgreSQL
- **Storage:** Google Drive (MP4s)
- **Auth:** Argon2id passwords, HTTP-only signed session cookies
- **Sharing:** Prepared MP4 file through the Web Share API, with an explicit MP4 download option where file sharing is unsupported

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# Edit .env — set DATABASE_URL and SECRET_KEY at minimum.
# Production additionally requires GOOGLE_SERVICE_ACCOUNT,
# GOOGLE_DRIVE_ROOT_FOLDER_ID, and COOKIE_SECURE=true.

# 4. Run database migrations
alembic upgrade head

# 5. Seed categories
python -m scripts.seed_categories

# 6. Start the development server
uvicorn app.main:app --reload

# 7. Open API docs
# http://localhost:8000/api/docs
```

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
quranflow/
├── app/
│   ├── main.py              # FastAPI app and router registration
│   ├── config.py            # Pydantic settings from environment
│   ├── database.py          # SQLAlchemy engine, session, Base
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routes/              # FastAPI routers (HTTP layer)
│   ├── services/            # Business logic
│   ├── dependencies/        # FastAPI dependency injection (auth, etc.)
│   └── utils/               # Security helpers
├── alembic/                 # Database migrations
├── scripts/                 # One-off utility scripts
├── tests/                   # Pytest test suite
├── .env.example             # Environment variable template
├── requirements.txt
└── alembic.ini
```

## Environment Variables

See `.env.example` for all required and optional variables.
**Never commit `.env` to version control.**

For production, the application refuses to start if Google Drive or
secure-cookie settings are incomplete. The scheduled-sync secret
(`CRON_SECRET`) is optional at boot — when unset, the sync endpoint
simply returns `403` and the rest of the app keeps working.

## Scheduled Drive Sync

The Google Drive → catalog sync runs every 15 minutes via the GitHub
Actions workflow at `.github/workflows/drive-sync.yml`, which calls
`POST /api/v1/admin/sync/google-drive-cron`.

> Vercel Cron on the **Hobby** plan only supports **once-per-day**
> schedules, and a more frequent expression fails the entire deployment.
> That is why the schedule lives in GitHub Actions instead.

Set up (once):

1. Generate a secret:
   `python -c "import secrets; print(secrets.token_hex(32))"`
2. Add it to **Vercel** → Project → Settings → Environment Variables as
   `CRON_SECRET` (Production and Preview).
3. Add the **same** value to **GitHub** → Repo → Settings → Secrets and
   variables → Actions as a secret named `CRON_SECRET`.
4. Optional: add a repository **variable** `SYNC_URL` to override the
   default endpoint (`https://quranshare-eta.vercel.app/api/v1/admin/sync/google-drive-cron`).

Curators/admins can still run a manual sync via
`POST /api/v1/admin/sync/google-drive`.

## Quran Foundation Content

The optional Quran Foundation Content API integration supplies the Qur'an
verse of the day through `GET /api/v1/content/verse-of-day`. Configure
`QF_CLIENT_ID`, `QF_CLIENT_SECRET`, `QF_ENV` (`prelive` or `production`), and
`QF_TRANSLATION_ID` in the server environment. The client secret stays on the
backend; the backend obtains and caches OAuth2 Content API tokens.

The Content API serves Qur'an content and translations, not a daily Du'a
collection. The Du'as screen therefore continues to use the three existing
local entries. Their source metadata is not present in this repository; the
details view says so instead of inventing references. Add further Du'as only
from a reviewed, appropriately licensed dataset with traceable source details.
