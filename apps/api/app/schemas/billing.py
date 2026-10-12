"""Billing / credits schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PlanRead(BaseModel):
    id: str
    name: str
    price_usd_month: float
    monthly_credits: int
    features: list[str]
    stripe_price_id: str | None = None
    is_current: bool = False


class CreditPackRead(BaseModel):
    id: str
    name: str
    credits: int
    price_usd: float
    stripe_price_id: str | None = None


class CheckoutRequest(BaseModel):
    kind: str = Field(pattern="^(subscription|credits)$")
    price_id: str | None = None
    plan: str | None = Field(default=None, pattern="^(pro|business)$")
    pack: str | None = Field(default=None, pattern="^(credits_100|credits_500|credits_2000)$")
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutSession(BaseModel):
    url: str
    session_id: str


class PortalSession(BaseModel):
    url: str


class BillingSummary(ORMModel):
    plan: str
    credits_balance: int
    monthly_allowance: int
    billing_enabled: bool
    stripe_customer_id: str | None = None
