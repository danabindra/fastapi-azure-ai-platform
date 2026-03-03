"""Health and version response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessCheck(BaseModel):
    database: bool
    keyvault: bool | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: ReadinessCheck


class VersionResponse(BaseModel):
    git_sha: str
    build_time: str
    app_env: str
