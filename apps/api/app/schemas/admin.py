"""Admin schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AdminUserRead(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    plan: str
    is_active: bool
    is_verified: bool
    credits_balance: int
    created_at: datetime
    last_login_at: datetime | None


class UsageSummary(ORMModel):
    total_users: int = 0
    total_books: int = 0
    total_jobs: int = 0
    failed_jobs: int = 0
    running_jobs: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    credits_consumed: int = 0


class AdminJobRead(ORMModel):
    id: uuid.UUID
    book_id: uuid.UUID
    user_id: uuid.UUID
    type: str
    status: str
    current_step: str | None
    progress_pct: int
    error: str | None
    attempts: int
    created_at: datetime
    finished_at: datetime | None


class AgentCostRow(ORMModel):
    agent_name: str
    runs: int
    tokens: int
    cost_usd: float
    failures: int


class AdminUserUpdate(BaseModel):
    """Partial update applied by an administrator."""

    full_name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    plan: str | None = Field(default=None, pattern="^(free|pro|business)$")
    is_active: bool | None = None
    is_verified: bool | None = None
    # Positive grants credits, negative debits them (reason: adjustment).
    credits_delta: int | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    credits_note: str | None = Field(default=None, max_length=300)
