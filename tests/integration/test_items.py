"""Integration tests for CRUD item endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_item(client: AsyncClient) -> None:
    resp = await client.post("/items", json={"name": "Test Item", "description": "A test"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["data"]["name"] == "Test Item"
    assert data["data"]["description"] == "A test"
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_get_item(client: AsyncClient) -> None:
    create_resp = await client.post("/items", json={"name": "Fetch Me"})
    item_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == item_id


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient) -> None:
    resp = await client.get("/items/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_items(client: AsyncClient) -> None:
    await client.post("/items", json={"name": "Item 1"})
    await client.post("/items", json={"name": "Item 2"})

    resp = await client.get("/items")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_list_items_pagination(client: AsyncClient) -> None:
    for i in range(5):
        await client.post("/items", json={"name": f"Paged {i}"})

    resp = await client.get("/items?skip=0&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) <= 2
    assert data["limit"] == 2


@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient) -> None:
    create_resp = await client.post("/items", json={"name": "Delete Me"})
    item_id = create_resp.json()["data"]["id"]

    del_resp = await client.delete(f"/items/{item_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/items/{item_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_item_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/items/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_item_validation_error(client: AsyncClient) -> None:
    resp = await client.post("/items", json={"name": ""})
    assert resp.status_code in (422, 400)


@pytest.mark.asyncio
async def test_correlation_id_in_response(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert "x-correlation-id" in resp.headers
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_correlation_id_passthrough(client: AsyncClient) -> None:
    custom_id = "my-trace-12345"
    resp = await client.get("/healthz", headers={"X-Correlation-ID": custom_id})
    assert resp.headers.get("x-correlation-id") == custom_id
