"""Shared pytest fixtures for unit and integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force local/test settings before any app module is imported
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("USE_KEYVAULT", "false")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.config import get_settings  # noqa: E402
from app.infra.db import Base, get_session  # noqa: E402
from app.main import create_app  # noqa: E402

# Clear settings cache so test env vars are picked up
get_settings.cache_clear()


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[Any, None]:
    """In-memory SQLite engine for unit tests."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with an overridden DB session."""

    # Patch init_db and close_db so lifespan doesn't try to connect to a real DB
    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.main.resolve_database_url", new_callable=AsyncMock, return_value=TEST_DB_URL),
    ):
        app = create_app()

        async def _override_session() -> AsyncGenerator[AsyncSession, None]:
            yield db_session

        app.dependency_overrides[get_session] = _override_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
