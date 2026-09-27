from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# Force Neon Postgres connection string, overriding any Vercel environment variables
_is_sqlite = False
_engine_kwargs: dict = {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}

db_url = "postgresql://quranshare_owner:npg_8goRHeI7PLld@ep-royal-band-b57qq2yr-pooler.c-7.us-east-2.aws.neon.tech/quranshare?sslmode=require&channel_binding=require"


engine = create_engine(db_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
