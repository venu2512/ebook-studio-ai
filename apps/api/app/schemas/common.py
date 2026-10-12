"""Shared API schemas: base config, pagination and envelopes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response models read directly from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """The single error shape returned by every endpoint."""

    error: ErrorDetail


class Page(BaseModel, Generic[T]):  # noqa: UP046 - Pydantic generic models prefer Generic[T]
    """Envelope for list endpoints."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def build(cls, items: Sequence[T], total: int, limit: int, offset: int) -> Page[T]:
        return cls(items=list(items), total=total, limit=limit, offset=offset)


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
