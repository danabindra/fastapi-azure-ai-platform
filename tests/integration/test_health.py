"""Integration tests for health endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_db_ok(client: AsyncClient) -> None:
    with patch("app.api.health.check_db_connection", new_callable=AsyncMock, return_value=True):
        resp = await client.get("/readyz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["checks"]["database"] is True


@pytest.mark.asyncio
async def test_readyz_db_fail(client: AsyncClient) -> None:
    with patch("app.api.health.check_db_connection", new_callable=AsyncMock, return_value=False):
        resp = await client.get("/readyz")
    assert resp.status_code == 200  # endpoint returns 200; status field signals degraded
    data = resp.json()
    assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_version(client: AsyncClient) -> None:
    resp = await client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "git_sha" in data
    assert "app_env" in data
