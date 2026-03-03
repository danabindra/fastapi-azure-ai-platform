"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.infra.db import check_db_connection
from app.schemas.health import HealthResponse, ReadinessCheck, ReadinessResponse, VersionResponse

router = APIRouter(tags=["Health"])


@router.get("/healthz", response_model=HealthResponse, summary="Liveness probe")
async def healthz() -> HealthResponse:
    """Always returns 200 OK; used by ACA as a liveness probe."""
    return HealthResponse()


@router.get(
    "/readyz",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={503: {"description": "Service not ready"}},
)
async def readyz(settings: Settings = Depends(get_settings)) -> ReadinessResponse:
    """Check database connectivity and (optionally) Key Vault authentication.

    Returns 200 when all critical checks pass, 503 when degraded.
    """
    db_ok = await check_db_connection()

    kv_ok: bool | None = None
    if settings.use_keyvault and settings.keyvault_url:
        kv_ok = await _check_keyvault(settings)

    all_ok = db_ok and (kv_ok is None or kv_ok)
    checks = ReadinessCheck(database=db_ok, keyvault=kv_ok)

    return ReadinessResponse(
        status="ok" if all_ok else "degraded",
        checks=checks,
    )


async def _check_keyvault(settings: Settings) -> bool:
    """Return True if Key Vault is accessible."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=settings.keyvault_url, credential=credential)
        # List secrets with max 1 result just to test auth; don't retrieve values.
        next(iter(client.list_properties_of_secrets(max_page_size=1)), None)
        return True
    except Exception:
        return False


@router.get("/version", response_model=VersionResponse, summary="Service version")
async def version(settings: Settings = Depends(get_settings)) -> VersionResponse:
    """Return git SHA, build time, and current environment."""
    return VersionResponse(
        git_sha=settings.git_sha,
        build_time=settings.build_time,
        app_env=settings.app_env,
    )
