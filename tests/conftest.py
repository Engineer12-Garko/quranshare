"""
Shared pytest fixtures for QuranFlow tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# In-memory SQLite for unit/integration tests (fast, no external DB needed)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Yields a database session that rolls back after each test.

    Uses a savepoint so that service-level db.commit() calls don't
    actually commit to the outer transaction, keeping tests isolated.
    """
    connection = engine.connect()
    transaction = connection.begin()
    # Bind session to the same connection so it participates in our transaction
    session = TestingSessionLocal(bind=connection)
    # Begin a savepoint; session.commit() will release/renew it instead of
    # committing to the DB.
    connection.begin_nested()

    from sqlalchemy import event

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction_):
        if transaction_.nested and not transaction_._parent.nested:
            # Restart the savepoint after each ORM-level commit
            connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    """FastAPI test client that uses the test database session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
