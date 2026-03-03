"""FastAPI application factory and lifecycle management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, items
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationMiddleware
from app.core.telemetry import instrument_app, setup_telemetry
from app.infra.db import close_db, init_db
from app.infra.keyvault import resolve_database_url
from app.schemas.common import ErrorResponse

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info(
        "app.startup",
        env=settings.app_env,
        git_sha=settings.git_sha,
        auth_enabled=settings.auth_enabled,
        use_keyvault=settings.use_keyvault,
    )

    # Resolve DB URL (may pull password from Key Vault)
    database_url = await resolve_database_url(settings)

    await init_db(
        database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )

    yield

    logger.info("app.shutdown")
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    # OTel must be configured before the app object is instrumented
    setup_telemetry(settings)

    app = FastAPI(
        title="FastAPI Azure AI Governance Starter",
        description=(
            "Production-grade FastAPI service demonstrating Azure-native patterns: "
            "Managed Identity, Key Vault, OpenTelemetry, and Terraform IaC."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (order matters: first added = outermost) ───────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(items.router)

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse.of(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.of(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            ).model_dump(),
        )

    instrument_app(app)
    return app


app = create_app()
