"""Book and outline models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.chapter import Chapter
    from app.db.models.export import Export
    from app.db.models.job import Job
    from app.db.models.marketing import MarketingKit
    from app.db.models.research import ResearchNote
    from app.db.models.user import User


class Book(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "books"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # --- Brief -----------------------------------------------------------------
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(400), nullable=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(400), nullable=False, default="General readers")
    category: Mapped[str] = mapped_column(String(120), nullable=False, default="General")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    tone: Mapped[str] = mapped_column(String(50), nullable=False, default="conversational")
    style_guide: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    target_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    author_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- State -----------------------------------------------------------------
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    # Estimated credit cost shown to the user before generation.
    estimated_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credits_charged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Hard per-book token budget enforced by the orchestrator.
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False, default=250_000)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    # "Book bible": running voice/terms/summaries shared with every Writer call.
    bible: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="books")
    outline_versions: Mapped[list[BookOutline]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="BookOutline.version",
    )
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Chapter.order_index",
    )
    jobs: Mapped[list[Job]] = relationship(back_populates="book", cascade="all, delete-orphan")
    research_notes: Mapped[list[ResearchNote]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    assets: Mapped[list[Asset]] = relationship(
        back_populates="book", cascade="all, delete-orphan", foreign_keys="Asset.book_id"
    )
    exports: Mapped[list[Export]] = relationship(back_populates="book", cascade="all, delete-orphan")
    marketing_kit: Mapped[MarketingKit | None] = relationship(
        back_populates="book", uselist=False, cascade="all, delete-orphan"
    )
    cover_asset: Mapped[Asset | None] = relationship(foreign_keys=[cover_asset_id], post_update=True)

    __table_args__ = (
        Index("ix_books_user_status", "user_id", "status"),
        Index("ix_books_user_deleted", "user_id", "deleted_at"),
    )

    @property
    def is_sensitive(self) -> bool:
        from app.db.models.enums import SENSITIVE_CATEGORIES

        return self.category.strip().lower() in SENSITIVE_CATEGORIES

    @property
    def total_word_count(self) -> int:
        return sum(c.word_count or 0 for c in self.chapters)


class BookOutline(UUIDMixin, TimestampMixin, Base):
    """A versioned outline. Only the approved version drives writing."""

    __tablename__ = "book_outlines"

    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # {title_options, subtitle, reader_promise, parts:[{title, chapters:[{title,
    #  summary, key_points:[], word_budget}]}], total_word_budget}
    structure: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    total_word_budget: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_by_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    book: Mapped[Book] = relationship(back_populates="outline_versions")

    @property
    def is_approved(self) -> bool:
        return self.approved_at is not None

    @property
    def chapter_count(self) -> int:
        return sum(len(part.get("chapters", [])) for part in self.structure.get("parts", []))
