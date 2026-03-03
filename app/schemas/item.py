"""Pydantic schemas for the Item resource."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Widget A"])
    description: str | None = Field(
        default=None,
        max_length=2000,
        examples=["A useful widget"],
    )

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class ItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
