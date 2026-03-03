"""Unit tests for configuration validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_are_valid() -> None:
    s = Settings()
    assert s.app_env == "local"
    assert s.auth_enabled is False
    assert s.use_keyvault is False
    assert s.is_production is False


def test_auth_requires_issuer_and_audience() -> None:
    with pytest.raises(ValidationError, match="ENTRA_ISSUER"):
        Settings(auth_enabled=True, entra_issuer="", entra_audience="api://foo")


def test_keyvault_requires_url() -> None:
    with pytest.raises(ValidationError, match="KEYVAULT_URL"):
        Settings(use_keyvault=True, keyvault_url="")


def test_production_flag() -> None:
    s = Settings(app_env="production")
    assert s.is_production is True


def test_otel_enabled_with_connection_string() -> None:
    s = Settings(applicationinsights_connection_string="InstrumentationKey=abc")
    assert s.otel_enabled is True


def test_otel_disabled_by_default() -> None:
    s = Settings()
    assert s.otel_enabled is False
