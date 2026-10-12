"""Export schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ExportCreateRequest(BaseModel):
    format: str = Field(pattern="^(pdf|epub|docx)$")
    template: str = Field(default="classic", max_length=80)
    page_size: str = Field(default="a5", pattern="^(a5|letter|a4)$")
    include_front_matter: bool = True
    include_toc: bool = True


class ExportRead(ORMModel):
    id: uuid.UUID
    book_id: uuid.UUID
    format: str
    template: str
    status: str
    size_bytes: int
    page_count: int | None
    checksum: str | None
    validation: dict[str, Any]
    error: str | None
    renderer: str | None
    created_at: datetime


class ExportDownload(BaseModel):
    export_id: uuid.UUID
    url: str
    expires_in: int
    filename: str
    size_bytes: int


class TemplateRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    kind: str
    description: str | None
    config: dict[str, Any]
    preview_url: str | None
    is_premium: bool


class CoverRegenerateRequest(BaseModel):
    prompt: str | None = Field(default=None, max_length=2000)
    style: str | None = Field(default=None, max_length=100)


class CoverRead(ORMModel):
    asset_id: uuid.UUID | None
    url: str | None
    prompt: str | None
    palette: dict[str, str] = Field(default_factory=dict)
