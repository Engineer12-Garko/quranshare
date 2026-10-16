"""Tests for production configuration validation."""
import pytest

from app.config import Settings


def _prod_kwargs(**overrides):
    data = dict(
        database_url="postgresql://user:pass@localhost:5432/db",
        secret_key="test-secret-key-that-is-long-enough-1234567890",
        app_env="production",
        google_service_account='{"type": "service_account"}',
        google_drive_root_folder_id="folder-123",
        cookie_secure=True,
    )
    data.update(overrides)
    return data


def test_production_boots_without_cron_secret():
    """A missing sync secret must NOT stop the whole app from starting.

    The scheduled-sync endpoint returns 403 when the secret is unset,
    but the application itself must remain healthy.
    """
    settings = Settings(**_prod_kwargs())
    assert settings.app_env == "production"


def test_production_requires_google_service_account():
    with pytest.raises(ValueError, match="GOOGLE_SERVICE_ACCOUNT"):
        Settings(**_prod_kwargs(google_service_account="{}"))


def test_production_requires_drive_root_folder():
    with pytest.raises(ValueError, match="GOOGLE_DRIVE_ROOT_FOLDER_ID"):
        Settings(**_prod_kwargs(google_drive_root_folder_id=""))


def test_production_requires_secure_cookie():
    with pytest.raises(ValueError, match="COOKIE_SECURE=true"):
        Settings(**_prod_kwargs(cookie_secure=False))
