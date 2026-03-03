"""Unit tests for Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.item import ItemCreate


def test_item_create_valid() -> None:
    item = ItemCreate(name="Widget", description="A test widget")
    assert item.name == "Widget"
    assert item.description == "A test widget"


def test_item_create_name_stripped() -> None:
    item = ItemCreate(name="  spaced  ")
    assert item.name == "spaced"


def test_item_create_blank_name_rejected() -> None:
    with pytest.raises(ValidationError, match="name must not be blank"):
        ItemCreate(name="   ")


def test_item_create_name_too_long() -> None:
    with pytest.raises(ValidationError):
        ItemCreate(name="x" * 256)


def test_item_create_description_optional() -> None:
    item = ItemCreate(name="Widget")
    assert item.description is None
