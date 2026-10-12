"""Billing routes: plans, credit packs, summary, checkout, portal and webhooks.

When ``STRIPE_SECRET_KEY`` is unset the app runs in "no billing" mode: credits
still work, checkout/portal return a clear 400 and the webhook refuses events.
All Stripe webhook handlers are idempotent (keyed by the Stripe event id).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.ratelimit import rate_limit
from app.schemas.billing import (
    BillingSummary,
    CheckoutRequest,
    CheckoutSession,
    CreditPackRead,
    PlanRead,
    PortalSession,
)
from app.services import billing as billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanRead])
async def list_plans(user: CurrentUser) -> list[PlanRead]:
    return [PlanRead(**plan) for plan in billing_service.list_plans(user.plan)]


@router.get("/credits/packs", response_model=list[CreditPackRead])
async def list_credit_packs(_: CurrentUser) -> list[CreditPackRead]:
    return [CreditPackRead(**pack) for pack in billing_service.list_credit_packs()]


@router.get("/summary", response_model=BillingSummary)
async def billing_summary(user: CurrentUser) -> BillingSummary:
    settings = get_settings()
    return BillingSummary(
        plan=user.plan,
        credits_balance=user.credits_balance,
        monthly_allowance=settings.plan_credits(user.plan),
        billing_enabled=settings.billing_enabled,
        stripe_customer_id=user.stripe_customer_id,
    )


@router.post(
    "/checkout",
    response_model=CheckoutSession,
    dependencies=[Depends(rate_limit("checkout", 20, 3600))],
)
async def create_checkout(
    payload: CheckoutRequest, user: CurrentUser, db: SessionDep
) -> CheckoutSession:
    result = await billing_service.create_checkout(
        db,
        user,
        kind=payload.kind,
        price_id=payload.price_id,
        plan=payload.plan,
        pack=payload.pack,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    return CheckoutSession(**result)


@router.post("/portal", response_model=PortalSession)
async def create_portal(user: CurrentUser, db: SessionDep) -> PortalSession:
    result = await billing_service.create_portal(db, user)
    return PortalSession(**result)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: SessionDep) -> dict:
    """Stripe webhook receiver. Verifies the signature before trusting data."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    event = billing_service.construct_event(payload, signature)
    return await billing_service.handle_event(db, event)
