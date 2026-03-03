"""Shared response envelope and pagination schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Consistent top-level response envelope."""

    data: T
    message: str = "ok"


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""

    data: list[T]
    total: int
    skip: int
    limit: int
    message: str = "ok"


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail

    @classmethod
    def of(
        cls,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> "ErrorResponse":
        return cls(error=ErrorDetail(code=code, message=message, details=details))
