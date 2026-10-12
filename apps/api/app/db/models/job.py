"""Job and AgentRun models - the resumable state machine and audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.book import Book


class Job(UUIDMixin, TimestampMixin, Base):
    """One generation run. Tracks progress and the resume point."""

    __tablename__ = "jobs"

    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="full_book")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)

    # Name of the step currently running (agent name or pipeline stage).
    current_step: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # Ordered list of completed step keys, used to resume after a restart.
    completed_steps: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optional per-chapter scope for chapter/export/covers jobs.
    target_chapter_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Number of retries attempted so far (used by POST /jobs/{id}/retry).
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Credits reserved for this job (charged on success, released on failure).
    reserved_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    charged: Mapped[bool] = mapped_column(default=False, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(default=False, nullable=False)

    input_params: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    book: Mapped[Book] = relationship(back_populates="jobs")
    agent_runs: Mapped[list[AgentRun]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="AgentRun.created_at"
    )

    __table_args__ = (
        Index("ix_jobs_book_status", "book_id", "status"),
        Index("ix_jobs_user_status", "user_id", "status"),
    )

    @property
    def is_terminal(self) -> bool:
        return self.status in {"succeeded", "failed", "cancelled"}


class AgentRun(UUIDMixin, TimestampMixin, Base):
    """Audit trail for a single agent invocation. Doubles as the resume point."""

    __tablename__ = "agent_runs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )

    agent_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    # Stable hash of the agent input - lets us detect/skip identical re-runs.
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Deterministic step key used to resume a pipeline (e.g. "writer:2").
    step_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    output: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    job: Mapped[Job] = relationship(back_populates="agent_runs")

    __table_args__ = (Index("ix_agent_runs_job_step", "job_id", "step_key"),)
