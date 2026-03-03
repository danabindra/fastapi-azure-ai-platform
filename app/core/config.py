"""Application configuration via pydantic-settings.

All settings are read from environment variables (and optionally a .env file).
Secrets in production are pulled from Azure Key Vault at startup, not here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"
    git_sha: str = "unknown"
    build_time: str = ""

    # ── Database ──────────────────────────────────────────────────────────────
    # In prod the password component is replaced by the Key Vault secret.
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/governance",
        description="Async SQLAlchemy database URL",
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # ── Key Vault ─────────────────────────────────────────────────────────────
    use_keyvault: bool = False
    keyvault_url: str = ""
    # Secret name inside Key Vault that holds the DB password
    keyvault_db_password_secret: str = "DB-PASSWORD"

    # ── Auth ──────────────────────────────────────────────────────────────────
    auth_enabled: bool = False
    entra_issuer: str = ""
    entra_audience: str = ""

    # ── OpenTelemetry / Azure Monitor ─────────────────────────────────────────
    otel_service_name: str = "governance-starter"
    applicationinsights_connection_string: str = ""
    otel_exporter_otlp_endpoint: str = ""

    @model_validator(mode="after")
    def validate_auth(self) -> "Settings":
        if self.auth_enabled:
            if not self.entra_issuer:
                raise ValueError("ENTRA_ISSUER must be set when AUTH_ENABLED=true")
            if not self.entra_audience:
                raise ValueError("ENTRA_AUDIENCE must be set when AUTH_ENABLED=true")
        return self

    @model_validator(mode="after")
    def validate_keyvault(self) -> "Settings":
        if self.use_keyvault and not self.keyvault_url:
            raise ValueError("KEYVAULT_URL must be set when USE_KEYVAULT=true")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def otel_enabled(self) -> bool:
        return bool(
            self.applicationinsights_connection_string or self.otel_exporter_otlp_endpoint
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
