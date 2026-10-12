"""Job and progress-event schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class GenerateRequest(BaseModel):
    """Start a full-book or scoped generation run."""

    type: str = Field(default="full_book", pattern="^(full_book|chapter|cover|export)$")
    chapter_id: uuid.UUID | None = None
    format: str | None = Field(default=None, pattern="^(pdf|epub|docx)$")
    template: str | None = None
    force: bool = Field(default=False, description="Regenerate even completed chapters")


class JobRead(ORMModel):
    id: uuid.UUID
    book_id: uuid.UUID
    user_id: uuid.UUID
    type: str
    status: str
    current_step: str | None
    completed_steps: list[str]
    progress_pct: int
    error_code: str | None
    error: str | None
    attempts: int
    reserved_credits: int
    charged: bool
    started_at: datetime | None
    finished_at: datetime | None
    cancel_requested: bool
    created_at: datetime


class AgentRunRead(ORMModel):
    id: uuid.UUID
    job_id: uuid.UUID
    agent_name: str
    status: str
    attempt: int
    step_key: str | None
    model: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: int
    error: str | None
    created_at: datetime


class AgentRunDetail(AgentRunRead):
    output: dict[str, Any]
    prompt: str | None


class PipelineStep(BaseModel):
    """One card in the live generation view."""

    key: str
    agent: str
    label: str
    status: str  # pending | running | succeeded | failed | skipped
    detail: str | None = None
    progress_pct: int = 0
    elapsed_ms: int | None = None
    tokens: int = 0
    cost_usd: float = 0.0


class PipelineState(BaseModel):
    job_id: uuid.UUID
    status: str
    progress_pct: int
    steps: list[PipelineStep]
    message: str | None = None


class JobEvent(BaseModel):
    """Server-Sent Event envelope."""

    event: str  # progress | step_started | step_finished | step_failed | done | error | heartbeat
    job_id: uuid.UUID
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
