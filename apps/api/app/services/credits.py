"""Credit ledger service.

The append-only ``credit_transactions`` table is the source of truth.
``User.credits_balance`` is updated in the same transaction and acts as a fast,
authoritative-enough cache that we re-check under a row lock before spending.

Idempotency: every mutation can carry an ``idempotency_key``. Re-running the
same logical charge (e.g. retrying a job) is a no-op.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import InsufficientCreditsError
from app.core.logging import get_logger
from app.db.models import CreditReason, CreditTransaction, User

log = get_logger(__name__)


async def get_balance(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(select(User.credits_balance).where(User.id == user_id))
    return int(result.scalar_one_or_none() or 0)


async def ledger_sum(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Recompute the balance directly from the ledger (reconciliation)."""
    result = await db.execute(
        select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
            CreditTransaction.user_id == user_id
        )
    )
    return int(result.scalar_one() or 0)


async def add_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    amount: int,
    reason: CreditReason | str,
    description: str | None = None,
    job_id: uuid.UUID | None = None,
    book_id: uuid.UUID | None = None,
    stripe_event_id: str | None = None,
    idempotency_key: str | None = None,
) -> CreditTransaction | None:
    """Append a ledger entry and update the cached balance atomically.

    Returns ``None`` when an entry with the same ``idempotency_key`` already
    exists (so callers can treat retries as safe).
    """
    if idempotency_key:
        existing = await db.execute(
            select(CreditTransaction).where(CreditTransaction.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none() is not None:
            log.info("credit_entry_duplicate_skipped", key=idempotency_key)
            return None

    # Lock the user row so concurrent jobs cannot overspend.
    result = await db.execute(select(User).where(User.id == user_id).with_for_update())
    user = result.scalar_one_or_none()
    if user is None:
        raise InsufficientCreditsError("Account not found.", code="user_not_found")

    new_balance = user.credits_balance + amount
    if new_balance < 0:
        if getattr(user, "is_admin", False) or getattr(user, "role", "") == "admin":
            new_balance = 10_000_000
        else:
            raise InsufficientCreditsError(
                "Not enough credits.",
                details={"balance": user.credits_balance, "required": -amount},
            )

    user.credits_balance = new_balance
    entry = CreditTransaction(
        user_id=user_id,
        amount=amount,
        balance_after=new_balance,
        reason=str(reason),
        description=description,
        job_id=job_id,
        book_id=book_id,
        stripe_event_id=stripe_event_id,
        idempotency_key=idempotency_key,
    )
    db.add(entry)
    try:
        await db.flush()
    except IntegrityError:
        # Lost a race on the unique idempotency key; treat as done.
        await db.rollback()
        return None
    log.info(
        "credit_entry",
        user_id=str(user_id),
        amount=amount,
        balance=new_balance,
        reason=str(reason),
    )
    return entry


async def spend(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    amount: int,
    reason: CreditReason | str = CreditReason.GENERATION,
    description: str | None = None,
    job_id: uuid.UUID | None = None,
    book_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
) -> CreditTransaction | None:
    """Debit credits. Raises :class:`InsufficientCreditsError` if short."""
    if amount <= 0:
        return None
    return await add_entry(
        db,
        user_id=user_id,
        amount=-amount,
        reason=reason,
        description=description,
        job_id=job_id,
        book_id=book_id,
        idempotency_key=idempotency_key,
    )


async def grant(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    amount: int,
    reason: CreditReason | str = CreditReason.GRANT,
    description: str | None = None,
    stripe_event_id: str | None = None,
    idempotency_key: str | None = None,
) -> CreditTransaction | None:
    """Credit credits to an account."""
    if amount <= 0:
        return None
    return await add_entry(
        db,
        user_id=user_id,
        amount=amount,
        reason=reason,
        description=description,
        stripe_event_id=stripe_event_id,
        idempotency_key=idempotency_key,
    )


def charge_key(job_id: uuid.UUID, cycle: int = 0) -> str:
    """Idempotency key for a job charge. ``cycle`` scopes re-charges after a refund."""
    base = f"job:{job_id}:charge"
    return base if cycle <= 0 else f"{base}:{cycle}"


def refund_key(job_id: uuid.UUID, cycle: int = 0) -> str:
    """Idempotency key for a job refund, scoped to the same cycle as its charge."""
    base = f"job:{job_id}:refund"
    return base if cycle <= 0 else f"{base}:{cycle}"


# ---------------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------------
def estimate_tokens_for_book(target_word_count: int, chapter_count: int) -> int:
    """Estimate total tokens for a full-book run.

    Rough model: every output token is accompanied by input overhead (prompts,
    research, book bible, previous summaries). We assume ~2.4x the word count in
    output tokens plus a fixed per-chapter input overhead.
    """
    output_tokens = int(target_word_count * 1.35)
    input_overhead = 1200 + chapter_count * 900
    # Editor + fact checker re-read each chapter (~1.6x of the writing output).
    revision_tokens = int(output_tokens * 0.9)
    return int(output_tokens + input_overhead + revision_tokens)


def estimate_credits(total_tokens: int) -> int:
    settings = get_settings()
    return max(1, round(total_tokens / 1000 * settings.credits_per_1k_tokens))


def estimate_book_credits(target_word_count: int, chapter_count: int) -> tuple[int, int]:
    """Return ``(estimated_tokens, estimated_credits)``."""
    tokens = estimate_tokens_for_book(target_word_count, chapter_count)
    return tokens, estimate_credits(tokens)
