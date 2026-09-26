# QuranFlow

A curated Quranic/Islamic reminder video library with WhatsApp sharing.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic
- **Database:** PostgreSQL
- **Storage:** Google Drive (MP4s)
- **Auth:** Argon2id passwords, HTTP-only signed session cookies
- **Sharing:** Web Share API / wa.me fallback

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
# Edit .env — set DATABASE_URL and SECRET_KEY at minimum

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
