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

The optional Quran Foundation Content API integration supplies the existing
compatibility reader routes and verse of the day through these backend routes:

- `GET /api/v1/content/chapters`
- `GET /api/v1/content/chapters/{chapter_number}/verses?page=1&per_page=50`
- `GET /api/v1/content/verses/by-key/{chapter:verse}`
- `GET /api/v1/content/verse-of-day`

Configure
`QF_CLIENT_ID`, `QF_CLIENT_SECRET`, `QF_ENV` (`prelive` or `production`), and
`QF_TRANSLATION_ID` in the server environment. The client secret stays on the
backend; the backend obtains and caches OAuth2 Content API tokens. Prelive is
limited to Al-Fatihah and Al-Baqarah; the app filters the chapter picker to
those chapters and selects the daily verse only from content available in the
configured environment. Production credentials expose production resources.
Choose the translation resource ID enabled for that environment (for example,
the project default `85` in Prelive); IDs must be verified against
`/content/api/v4/resources/translations?language=en` for the active environment.
The client caches chapter metadata and daily content in memory; browser requests
also use bounded GET caching. Arabic text is marked RTL and `notranslate`.

## Live Quran and Du'a Providers

The reader also exposes a public, unauthenticated AlQuran Cloud compatibility
layer for all 114 surahs. It is used by the Qur'an reader while the existing
Quran Foundation routes remain available for verse of the day and compatibility:

- `GET /api/v1/content/quran/surahs`
- `GET /api/v1/content/quran/surahs/{surah_number}`

The selected English translation is `en.sahih` (Saheeh International), and
verse-by-verse `ar.alafasy` audio URLs are returned when available. AlQuran
Cloud requires no API key for these public endpoints. Responses are validated,
cached briefly in memory, and upstream failures are returned as sanitized
503/429 responses.

Du'as are loaded from the public OpenDua API without an API key:

- `GET /api/v1/duas/collections`
- `GET /api/v1/duas?search=...&category=...`
- `GET /api/v1/duas/{entry_id}`

OpenDua entries provide Arabic, transliteration, English translation, source
references, and recordings where available. The UI links attribution to
OpenDua and does not invent missing references. OpenDua's published data and
audio licences should be reviewed before redistributing or caching content
outside the short-lived server cache. No additional environment variables are
required. If either provider is unavailable or rate-limited, the backend
returns a sanitized error; the existing local Du'a entries remain a
compatibility fallback for the client and for previously saved items.
