"""Async SQLAlchemy engine and session factory.

The engine is initialised lazily on first use (or explicitly at startup via
`init_db`). Connection parameters are read from Settings after any Key Vault
resolution has taken place.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine not initialised; call init_db() first.")
    return _engine


async def init_db(database_url: str, **kwargs: Any) -> None:  # noqa: ANN401
    """Create the async engine and session factory.

    Called once at application startup after Key Vault resolution.
    """
    global _engine, _session_factory

    logger.info("db.init", url=_redact_url(database_url))

    _engine = create_async_engine(
        database_url,
        pool_size=kwargs.get("pool_size", 5),
        max_overflow=kwargs.get("max_overflow", 10),
        pool_timeout=kwargs.get("pool_timeout", 30),
        pool_pre_ping=True,
        echo=False,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("db.ready")


async def close_db() -> None:
    """Dispose the engine (called on application shutdown)."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("db.closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised; call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_connection() -> bool:
    """Return True if a DB connection can be established (used by /readyz)."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("db.health_check_failed", error=str(exc))
        return False


def _redact_url(url: str) -> str:
    """Remove password from URL for safe logging."""
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    if parsed.password:
        netloc = parsed.netloc.replace(f":{parsed.password}", ":***")
        return urlunparse(parsed._replace(netloc=netloc))
    return url
