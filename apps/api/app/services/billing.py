"""Billing service: Stripe checkout, portal and webhook handling.

Every webhook handler is idempotent (keyed by the Stripe event id) so Stripe's
at-least-once delivery cannot double-credit an account. When ``STRIPE_SECRET_KEY``
is unset the app runs in "no billing" mode: credits still work, checkout is
disabled and the endpoints return a clear message.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.db.models import CreditReason, Plan, Subscription, User
from app.services import credits as credits_service

log = get_logger(__name__)

_CUSTOMER_PLANS = {  # feature flags for GET /billing/plans
    "pro": ["2,000 credits / month", "All exports", "Marketing kit", "Priority queue"],
    "business": [
        "10,000 credits / month",
        "Team-ready exports",
        "Higher token budgets",
        "Priority support",
    ],
}


def _stripe():
    settings = get_settings()
    if not settings.billing_enabled:
        return None
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


def list_plans(current_plan: str = "free") -> list[dict]:
    settings = get_settings()
    return [
        {
            "id": "free",
            "name": "Free",
            "price_usd_month": 0.0,
            "monthly_credits": settings.free_plan_monthly_credits,
            "features": ["20-page books", "PDF / EPUB / DOCX", "AI cover"],
            "stripe_price_id": None,
            "is_current": current_plan == "free",
        },
        {
            "id": "pro",
            "name": "Pro",
            "price_usd_month": 19.0,
            "monthly_credits": settings.pro_plan_monthly_credits,
            "features": _CUSTOMER_PLANS["pro"],
            "stripe_price_id": settings.stripe_price_pro_monthly or None,
            "is_current": current_plan == "pro",
        },
        {
            "id": "business",
            "name": "Business",
            "price_usd_month": 49.0,
            "monthly_credits": settings.business_plan_monthly_credits,
            "features": _CUSTOMER_PLANS["business"],
            "stripe_price_id": settings.stripe_price_business_monthly or None,
            "is_current": current_plan == "business",
        },
    ]


def list_credit_packs() -> list[dict]:
    settings = get_settings()
    return [
        {
            "id": "credits_100",
            "name": "100 credits",
            "credits": 100,
            "price_usd": 9.0,
            "stripe_price_id": settings.stripe_price_credits_100 or None,
        },
        {
            "id": "credits_500",
            "name": "500 credits",
            "credits": 500,
            "price_usd": 39.0,
            "stripe_price_id": settings.stripe_price_credits_500 or None,
        },
        {
            "id": "credits_2000",
            "name": "2,000 credits",
            "credits": 2000,
            "price_usd": 129.0,
            "stripe_price_id": settings.stripe_price_credits_2000 or None,
        },
    ]


async def ensure_customer(db: AsyncSession, user: User) -> str | None:
    """Get or create the Stripe customer id for a user."""
    stripe = _stripe()
    if stripe is None:
        return None
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(email=user.email, name=user.full_name or user.email)
    user.stripe_customer_id = customer["id"]
    await db.flush()
    return customer["id"]


async def create_checkout(
    db: AsyncSession,
    user: User,
    *,
    kind: str,
    price_id: str | None,
    plan: str | None,
    pack: str | None,
    success_url: str | None,
    cancel_url: str | None,
) -> dict:
    stripe = _stripe()
    if stripe is None:
        raise AppError(
            "Billing is not configured on this deployment.",
            code="billing_disabled",
            status_code=400,
        )
    settings = get_settings()
    customer_id = await ensure_customer(db, user)

    resolved_price = price_id
    mode = "subscription" if kind == "subscription" else "payment"
    if resolved_price is None:
        if kind == "subscription":
            resolved_price = {
                "pro": settings.stripe_price_pro_monthly,
                "business": settings.stripe_price_business_monthly,
            }.get(plan or "", "")
        else:
            resolved_price = {
                "credits_100": settings.stripe_price_credits_100,
                "credits_500": settings.stripe_price_credits_500,
                "credits_2000": settings.stripe_price_credits_2000,
            }.get(pack or "", "")
    if not resolved_price:
        raise AppError("No Stripe price configured for that option.", code="price_not_configured")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode=mode,
        line_items=[{"price": resolved_price, "quantity": 1}],
        success_url=success_url or f"{settings.web_base_url}/billing?status=success",
        cancel_url=cancel_url or f"{settings.web_base_url}/billing?status=cancelled",
        client_reference_id=str(user.id),
        metadata={"user_id": str(user.id), "kind": kind, "plan": plan or "", "pack": pack or ""},
    )
    return {"url": session["url"], "session_id": session["id"]}


async def create_portal(db: AsyncSession, user: User) -> dict:
    stripe = _stripe()
    if stripe is None:
        raise AppError("Billing is not configured.", code="billing_disabled", status_code=400)
    settings = get_settings()
    customer_id = await ensure_customer(db, user)
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.web_base_url}/billing",
    )
    return {"url": session["url"]}


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------
def construct_event(payload: bytes, signature: str) -> dict:
    settings = get_settings()
    stripe = _stripe()
    if stripe is None:
        raise AppError("Billing is not configured.", code="billing_disabled", status_code=400)
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise AppError(
            "Invalid Stripe signature.", code="invalid_signature", status_code=400
        ) from exc
    return event


async def handle_event(db: AsyncSession, event: dict) -> dict:
    """Idempotently process a Stripe event. Returns a small result summary."""
    event_id = event.get("id", "")
    event_type = event.get("type", "")
    data = (event.get("data") or {}).get("object") or {}
    result = {"event_id": event_id, "type": event_type, "handled": False}

    if event_type == "checkout.session.completed":
        await _on_checkout_completed(db, data, event_id)
        result["handled"] = True
    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        await _on_subscription_upsert(db, data)
        result["handled"] = True
    elif event_type == "customer.subscription.deleted":
        await _on_subscription_deleted(db, data)
        result["handled"] = True
    elif event_type == "invoice.paid":
        await _on_invoice_paid(db, data, event_id)
        result["handled"] = True
    else:
        log.info("stripe_event_ignored", type=event_type)

    return result


async def _user_from_metadata(db: AsyncSession, data: dict) -> User | None:
    metadata = data.get("metadata") or {}
    user_id = metadata.get("user_id") or data.get("client_reference_id")
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return user
    customer_id = data.get("customer")
    if customer_id:
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        return result.scalar_one_or_none()
    return None


async def _on_checkout_completed(db: AsyncSession, data: dict, event_id: str) -> None:
    user = await _user_from_metadata(db, data)
    if user is None:
        log.warning("stripe_checkout_no_user", session=data.get("id"))
        return
    metadata = data.get("metadata") or {}
    kind = metadata.get("kind")

    if kind == "credits":
        amount = _credits_for_pack(metadata.get("pack", ""))
        await credits_service.grant(
            db,
            user_id=user.id,
            amount=amount,
            reason=CreditReason.PURCHASE,
            description=f"Credit pack purchase ({metadata.get('pack')})",
            stripe_event_id=event_id,
            idempotency_key=f"stripe:{event_id}",
        )
    elif kind == "subscription":
        plan = metadata.get("plan") or "pro"
        user.plan = plan
        amount = get_settings().plan_credits(plan)
        await credits_service.grant(
            db,
            user_id=user.id,
            amount=amount,
            reason=CreditReason.SUBSCRIPTION,
            description=f"{plan.title()} plan monthly credits",
            stripe_event_id=event_id,
            idempotency_key=f"stripe:{event_id}",
        )
    await db.flush()


def _credits_for_pack(pack: str) -> int:
    return {"credits_100": 100, "credits_500": 500, "credits_2000": 2000}.get(pack, 0)


async def _on_subscription_upsert(db: AsyncSession, data: dict) -> None:
    subscription_id = data.get("id")
    customer_id = data.get("customer")
    if not subscription_id:
        return
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if user is None:
        return

    status = data.get("status", "active")
    price_id = ((data.get("items") or {}).get("data") or [{}])[0].get("price", {}).get("id")
    plan = _plan_for_price(price_id) or user.plan

    existing = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    sub = existing.scalar_one_or_none()
    period_end = data.get("current_period_end")

    if sub is None:
        sub = Subscription(
            user_id=user.id,
            stripe_subscription_id=subscription_id,
            stripe_price_id=price_id,
            plan=plan,
            status=status,
        )
        db.add(sub)
    else:
        sub.status = status
        sub.plan = plan
        sub.stripe_price_id = price_id

    if period_end:
        sub.current_period_end = datetime.fromtimestamp(int(period_end), tz=UTC)
    sub.cancel_at_period_end = bool(data.get("cancel_at_period_end", False))

    # Drive the user's plan from subscription status.
    if status in ("active", "trialing"):
        user.plan = plan
    elif status in ("canceled", "unpaid", "incomplete_expired"):
        user.plan = Plan.FREE.value
    await db.flush()


async def _on_subscription_deleted(db: AsyncSession, data: dict) -> None:
    subscription_id = data.get("id")
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return
    sub.status = "canceled"
    user = await db.get(User, sub.user_id)
    if user:
        user.plan = Plan.FREE.value
    await db.flush()


async def _on_invoice_paid(db: AsyncSession, data: dict, event_id: str) -> None:
    """Grant the monthly allowance on each paid invoice (idempotent)."""
    customer_id = data.get("customer")
    if not customer_id:
        return
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if user is None:
        return
    amount = get_settings().plan_credits(user.plan)
    if amount <= 0:
        return
    await credits_service.grant(
        db,
        user_id=user.id,
        amount=amount,
        reason=CreditReason.SUBSCRIPTION,
        description=f"{user.plan.title()} plan monthly credits",
        stripe_event_id=event_id,
        idempotency_key=f"stripe:{event_id}",
    )
    await db.flush()


def _plan_for_price(price_id: str | None) -> str | None:
    settings = get_settings()
    mapping = {
        settings.stripe_price_pro_monthly: "pro",
        settings.stripe_price_business_monthly: "business",
    }
    return mapping.get(price_id or "")
