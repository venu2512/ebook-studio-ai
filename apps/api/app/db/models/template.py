"""Interior and cover templates."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Template(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="interior")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # {fonts, colors, page_size, margins, heading_style, ...}
    config: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    preview_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
