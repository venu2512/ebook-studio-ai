"""Export records for generated PDF / EPUB / DOCX files."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.book import Book


class Export(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "exports"

    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)

    format: Mapped[str] = mapped_column(String(10), nullable=False)
    template: Mapped[str] = mapped_column(String(80), nullable=False, default="classic")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validation: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    renderer: Mapped[str | None] = mapped_column(String(40), nullable=True)

    book: Mapped[Book] = relationship(back_populates="exports")

    __table_args__ = (Index("ix_exports_book_format", "book_id", "format"),)
