"""Chapter and chapter-version models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.book import Book


class Chapter(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chapters"

    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    part_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Editor-warning surface: unverified claims, style issues, etc.
    flags: Mapped[list[dict[str, Any]]] = mapped_column(default=list, nullable=False)
    # Fact-checker verdicts for this chapter.
    fact_checks: Mapped[list[dict[str, Any]]] = mapped_column(default=list, nullable=False)

    book: Mapped[Book] = relationship(back_populates="chapters")
    versions: Mapped[list[ChapterVersion]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="ChapterVersion.version",
    )

    __table_args__ = (
        UniqueConstraint("book_id", "order_index", name="uq_chapter_book_order"),
        Index("ix_chapters_book_status", "book_id", "status"),
    )


class ChapterVersion(UUIDMixin, TimestampMixin, Base):
    """Immutable snapshot enabling undo and safe regeneration."""

    __tablename__ = "chapter_versions"

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="agent")
    editor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    chapter: Mapped[Chapter] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("chapter_id", "version", name="uq_chapter_version"),
    )
