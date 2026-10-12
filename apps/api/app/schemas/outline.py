"""Outline schemas (generate, edit, approve)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class OutlineGenerateRequest(BaseModel):
    """Optional overrides when (re)generating an outline."""

    chapter_count: int | None = Field(default=None, ge=3, le=40)
    extra_instructions: str | None = Field(default=None, max_length=2000)
    reuse_research: bool = True


class OutlineChapter(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    word_budget: int = Field(default=0, ge=0)


class OutlinePart(BaseModel):
    title: str = "Part I"
    chapters: list[OutlineChapter] = Field(default_factory=list)


class OutlineUpdateRequest(BaseModel):
    """Send the whole structure back after editing in the UI."""

    structure: dict[str, Any]
    title: str | None = None
    subtitle: str | None = None
    reader_promise: str | None = None


class OutlineRead(ORMModel):
    id: uuid.UUID
    book_id: uuid.UUID
    version: int
    structure: dict[str, Any]
    total_word_budget: int
    approved_at: datetime | None
    created_at: datetime


class OutlineApprovalResponse(BaseModel):
    status: str
    approved_at: datetime
    chapter_count: int
    total_word_budget: int
