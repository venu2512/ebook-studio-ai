"""Book schemas and the guided-wizard payload."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator

from app.schemas.common import ORMModel

WORDS_PER_PAGE = 250

LANGUAGES = ["en", "es", "fr", "de", "pt", "it", "nl", "hi", "ja", "zh"]
TONES = ["conversational", "professional", "academic", "friendly", "authoritative", "motivational"]


class BookCreate(BaseModel):
    """Payload from the new-book wizard."""

    topic: str = Field(min_length=3, max_length=500)
    title: str | None = Field(default=None, max_length=300)
    audience: str = Field(default="General readers", max_length=400)
    category: str = Field(default="General", max_length=120)
    language: str = Field(default="en", max_length=10)
    tone: str = Field(default="conversational", max_length=50)
    target_pages: int = Field(default=20, ge=6, le=500)
    target_word_count: int | None = Field(default=None, ge=1500, le=150_000)
    style_guide: str | None = Field(default=None, max_length=4000)
    author_name: str | None = Field(default=None, max_length=200)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    template: str = Field(default="classic", max_length=80)
    chapter_count: int | None = Field(default=None, ge=3, le=40)

    @model_validator(mode="after")
    def _fill_word_count(self) -> BookCreate:
        if self.target_word_count is None:
            object.__setattr__(self, "target_word_count", self.target_pages * WORDS_PER_PAGE)
        return self


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    subtitle: str | None = Field(default=None, max_length=400)
    topic: str | None = Field(default=None, max_length=500)
    audience: str | None = Field(default=None, max_length=400)
    category: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=10)
    tone: str | None = Field(default=None, max_length=50)
    target_pages: int | None = Field(default=None, ge=6, le=500)
    target_word_count: int | None = Field(default=None, ge=1500, le=150_000)
    style_guide: str | None = Field(default=None, max_length=4000)
    author_name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    keywords: list[str] | None = None
    metadata_json: dict[str, Any] | None = None


class CostEstimate(BaseModel):
    estimated_tokens: int
    estimated_credits: int
    user_balance: int
    affordable: bool
    breakdown: dict[str, int] = Field(default_factory=dict)


class BookRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    subtitle: str | None
    topic: str
    audience: str
    category: str
    language: str
    tone: str
    style_guide: str | None
    target_pages: int
    target_word_count: int
    author_name: str | None
    status: str
    cover_asset_id: uuid.UUID | None
    description: str | None
    keywords: list[str]
    estimated_credits: int
    credits_charged: int
    token_budget: int
    tokens_used: int
    cost_usd: float
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_sensitive(self) -> bool:
        from app.db.models.enums import SENSITIVE_CATEGORIES

        return self.category.strip().lower() in SENSITIVE_CATEGORIES


class BookListItem(ORMModel):
    id: uuid.UUID
    title: str
    subtitle: str | None
    topic: str
    category: str
    language: str
    status: str
    target_pages: int
    target_word_count: int
    cover_asset_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class BookWithProgress(BookListItem):
    """Dashboard card: adds derived progress info."""

    chapter_count: int = 0
    completed_chapters: int = 0
    progress_pct: int = 0
    current_job_status: str | None = None
