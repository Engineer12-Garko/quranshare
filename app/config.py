from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str

    # Security
    secret_key: str
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # App
    app_env: Literal["development", "test", "production"] = "development"

    # Google Drive
    google_service_account: str = "{}"
    google_drive_root_folder_id: str = ""
    vercel_cron_secret: str = ""

    # Quran Foundation Content API (optional; Du'a records are not provided)
    qf_client_id: str = ""
    qf_client_secret: str = ""
    qf_env: Literal["prelive", "production"] = "prelive"
    qf_translation_id: str = "131"

    # Reminder
    recent_exclusion_limit: int = 7

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_default(cls, v: str) -> str:
        if v == "change-me-generate-a-real-secret":
            raise ValueError(
                "SECRET_KEY must be changed from the default value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @model_validator(mode="after")
    def production_settings_must_be_safe(self) -> "Settings":
        if self.app_env == "production":
            missing = []
            if not self.google_service_account or self.google_service_account == "{}":
                missing.append("GOOGLE_SERVICE_ACCOUNT")
            if not self.google_drive_root_folder_id:
                missing.append("GOOGLE_DRIVE_ROOT_FOLDER_ID")
            if not self.cookie_secure:
                missing.append("COOKIE_SECURE=true")
            if missing:
                raise ValueError(
                    "Production configuration is incomplete: " + ", ".join(missing)
                )
        return self


settings = Settings()
