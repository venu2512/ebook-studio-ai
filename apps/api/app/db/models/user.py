"""User account model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.billing import CreditTransaction, Subscription
    from app.db.models.book import Book


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    # Nullable because OAuth-only accounts have no password.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    plan: Mapped[str] = mapped_column(String(20), default="free", nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Cached ledger balance. The source of truth is ``credit_transactions``;
    # this column is updated atomically in the same transaction as each entry.
    credits_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    default_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    default_tone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    books: Mapped[list[Book]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    credit_transactions: Mapped[list[CreditTransaction]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_users_plan_active", "plan", "is_active"),)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def id_str(self) -> str:
        return str(self.id)


# Re-export for Alembic autogenerate visibility.
__all__ = ["User", "uuid"]
