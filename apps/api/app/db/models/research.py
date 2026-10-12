"""Research notes gathered by the Researcher agent."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.book import Book


class ResearchNote(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_notes"

    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 0.0 - 1.0 confidence; unverified findings are flagged rather than cited.
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    used_in_chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tags: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    extra: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    book: Mapped[Book] = relationship(back_populates="research_notes")

    __table_args__ = (Index("ix_research_book_verified", "book_id", "is_verified"),)
