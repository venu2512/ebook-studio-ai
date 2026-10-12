"""User and credits schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    avatar_url: str | None
    role: str
    plan: str
    is_verified: bool
    credits_balance: int
    default_language: str
    default_tone: str | None
    created_at: datetime
    last_login_at: datetime | None


class UserUpdate(ORMModel):
    full_name: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None, max_length=1024)
    default_language: str | None = Field(default=None, max_length=10)
    default_tone: str | None = Field(default=None, max_length=50)
    settings_json: dict | None = None


class CreditsRead(ORMModel):
    balance: int
    plan: str
    monthly_allowance: int
    credits_per_1k_tokens: int


class CreditTransactionRead(ORMModel):
    id: uuid.UUID
    amount: int
    balance_after: int
    reason: str
    description: str | None
    created_at: datetime


class DeleteAccountRequest(ORMModel):
    password: str | None = None
    confirm: bool = False
