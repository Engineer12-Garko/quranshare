import os

# Set required env vars before any app code is imported.
# Tests use SQLite in-memory so DATABASE_URL is not actually used for connections.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production-abc123")
os.environ.setdefault("APP_ENV", "test")
