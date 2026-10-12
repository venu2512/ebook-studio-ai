"""Credit ledger: balance, idempotency, refunds and estimation."""

from __future__ import annotations

import uuid

import pytest

from app.core.errors import InsufficientCreditsError
from app.services import credits as credits_service
from app.services import users as users_service


async def _make_user(db, *, credits: int | None = None):
    email = f"credits-{uuid.uuid4().hex[:10]}@example.com"
    user = await users_service.create_user(db, email=email, password="password123")
    if credits is not None:
        user.credits_balance = credits
        await db.flush()
    return user


async def test_signup_grants_free_plan_credits(db):
    user = await _make_user(db)
    assert user.credits_balance == 100
    assert await credits_service.get_balance(db, user.id) == 100
    assert await credits_service.ledger_sum(db, user.id) == 100


async def test_spend_and_grant_keep_ledger_in_sync(db):
    user = await _make_user(db)
    await credits_service.spend(db, user_id=user.id, amount=30, description="test")
    await credits_service.grant(db, user_id=user.id, amount=5, description="bonus")
    balance = await credits_service.get_balance(db, user.id)
    assert balance == 75
    assert balance == await credits_service.ledger_sum(db, user.id)


async def test_idempotency_key_prevents_double_spend(db):
    user = await _make_user(db)
    key = "job:abc:charge"
    first = await credits_service.spend(db, user_id=user.id, amount=40, idempotency_key=key)
    assert first is not None
    balance = await credits_service.get_balance(db, user.id)

    second = await credits_service.spend(db, user_id=user.id, amount=40, idempotency_key=key)
    assert second is None
    assert await credits_service.get_balance(db, user.id) == balance == 60


async def test_spend_more_than_balance_raises(db):
    user = await _make_user(db)
    with pytest.raises(InsufficientCreditsError) as exc:
        await credits_service.spend(db, user_id=user.id, amount=101)
    assert exc.value.code == "insufficient_credits"
    assert exc.value.details["required"] == 101
    # Balance is untouched.
    assert await credits_service.get_balance(db, user.id) == 100


async def test_spend_zero_is_a_noop(db):
    user = await _make_user(db)
    assert await credits_service.spend(db, user_id=user.id, amount=0) is None
    assert await credits_service.get_balance(db, user.id) == 100


async def test_charge_and_refund_keys_are_distinct():
    job_id = uuid.uuid4()
    assert credits_service.charge_key(job_id) == f"job:{job_id}:charge"
    assert credits_service.refund_key(job_id) == f"job:{job_id}:refund"
    assert credits_service.charge_key(job_id) != credits_service.refund_key(job_id)


def test_estimation_is_positive_and_monotonic():
    tokens_a, credits_a = credits_service.estimate_book_credits(5_000, 5)
    tokens_b, credits_b = credits_service.estimate_book_credits(10_000, 10)
    assert tokens_a > 0 and credits_a >= 1
    assert tokens_b > tokens_a
    assert credits_b > credits_a


def test_estimate_credits_rounds_to_at_least_one():
    assert credits_service.estimate_credits(0) == 1
    assert credits_service.estimate_credits(1) == 1
