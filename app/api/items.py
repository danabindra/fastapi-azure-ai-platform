"""CRUD endpoints for the Item resource."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.infra.db import get_session
from app.models.item import Item
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.item import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["Items"])

# Type alias for the auth dependency result
AuthPayload = Annotated[dict[str, Any] | None, Depends(verify_token)]
DB = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "",
    response_model=APIResponse[ItemRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
)
async def create_item(
    body: ItemCreate,
    session: DB,
    _auth: AuthPayload,
) -> APIResponse[ItemRead]:
    item = Item(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return APIResponse(data=ItemRead.model_validate(item), message="created")


@router.get(
    "/{item_id}",
    response_model=APIResponse[ItemRead],
    summary="Get an item by ID",
    responses={404: {"description": "Item not found"}},
)
async def get_item(
    item_id: str,
    session: DB,
    _auth: AuthPayload,
) -> APIResponse[ItemRead]:
    item = await session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return APIResponse(data=ItemRead.model_validate(item))


@router.get(
    "",
    response_model=PaginatedResponse[ItemRead],
    summary="List items with pagination",
)
async def list_items(
    session: DB,
    _auth: AuthPayload,
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return"),
) -> PaginatedResponse[ItemRead]:
    total_result = await session.execute(select(func.count()).select_from(Item))
    total: int = total_result.scalar_one()

    items_result = await session.execute(
        select(Item).order_by(Item.created_at.desc()).offset(skip).limit(limit)
    )
    items = list(items_result.scalars().all())

    return PaginatedResponse(
        data=[ItemRead.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
    responses={404: {"description": "Item not found"}},
)
async def delete_item(
    item_id: str,
    session: DB,
    _auth: AuthPayload,
) -> None:
    item = await session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await session.delete(item)
