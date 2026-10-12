"""Chapter and version schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ChapterRead(ORMModel):
    id: uuid.UUID
    book_id: uuid.UUID
    order_index: int
    part_title: str | None
    title: str
    summary: str | None
    key_points: list[str]
    content: str | None
    word_count: int
    target_word_count: int
    status: str
    current_version: int
    flags: list[dict[str, Any]]
    fact_checks: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class ChapterListItem(ORMModel):
    id: uuid.UUID
    order_index: int
    title: str
    status: str
    word_count: int
    target_word_count: int
    part_title: str | None
    updated_at: datetime


class ChapterUpdate(BaseModel):
    """Editor save. Content is markdown."""

    title: str | None = Field(default=None, max_length=400)
    content: str | None = None
    summary: str | None = None
    status: str | None = None
    editor_notes: str | None = Field(default=None, max_length=2000)
    create_version: bool = True


class ChapterRegenerateRequest(BaseModel):
    instructions: str | None = Field(default=None, max_length=2000)
    preserve_title: bool = True


class AIActionRequest(BaseModel):
    """Inline AI actions in the editor."""

    action: str = Field(pattern="^(rewrite|expand|shorten|change_tone|improve)$")
    tone: str | None = Field(default=None, max_length=50)
    selection: str | None = Field(default=None, max_length=20000)
    instructions: str | None = Field(default=None, max_length=2000)


class AIActionResponse(BaseModel):
    chapter_id: uuid.UUID
    action: str
    content: str
    word_count: int
    flags: list[dict[str, Any]] = Field(default_factory=list)


class ChapterVersionRead(ORMModel):
    id: uuid.UUID
    chapter_id: uuid.UUID
    version: int
    word_count: int
    source: str
    editor_notes: str | None
    created_at: datetime


class ChapterVersionDetail(ChapterVersionRead):
    content: str


class ChapterRestoreRequest(BaseModel):
    version: int = Field(ge=1)
