"""Marketing kit produced by the Marketing Specialist agent."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.book import Book


class MarketingKit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "marketing_kits"

    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    categories: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    bullet_points: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    # [{"platform": "twitter", "text": "..."}]
    social_posts: Mapped[list[dict[str, Any]]] = mapped_column(default=list, nullable=False)
    # [{"day": 1, "subject": "...", "body": "..."}]
    email_sequence: Mapped[list[dict[str, Any]]] = mapped_column(default=list, nullable=False)
    author_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    kdp_categories: Mapped[list[str]] = mapped_column(default=list, nullable=False)

    book: Mapped[Book] = relationship(back_populates="marketing_kit")
