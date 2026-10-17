"""Job service: creation, credit reservation, dispatch, cancel, retry.

Charging model (predictable, exactly once):

1. Estimate the credit cost up front and check the balance.
2. Debit once, keyed by ``job:<id>:charge`` (idempotent).
3. If the job fails/cancels having produced nothing, refund once, keyed by
   ``job:<id>:refund``.
4. Retrying a job does **not** re-charge a job that still holds its charge. A
   job that was refunded (nothing produced) is charged again under a new
   per-attempt key, so a retry is never free.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, InsufficientCreditsError, NotFoundError
from app.core.logging import get_logger
from app.db.models import AgentRun, Book, CreditReason, Job, User
from app.services import credits as credits_service

log = get_logger(__name__)

# Per-job-type credit multipliers relative to the full-book estimate.
COST_FACTORS: dict[str, float] = {
    "full_book": 1.0,
    "outline": 0.15,
    "chapter": 0.12,
    "cover": 0.03,
    "export": 0.01,
}

# Keep strong references to inline tasks so they are not garbage collected.
_inline_tasks: set[asyncio.Task] = set()


def estimate_job_credits(book: Book, job_type: str) -> int:
    base = max(1, book.estimated_credits or 1)
    factor = COST_FACTORS.get(job_type, 0.1)
    return max(1, round(base * factor))


async def create_job(
    db: AsyncSession,
    user: User,
    book: Book,
    *,
    job_type: str = "full_book",
    target_chapter_id: uuid.UUID | None = None,
    input_params: dict[str, Any] | None = None,
    charge: bool = True,
) -> Job:
    """Create a job, charge its estimated credits and enqueue execution."""
    input_params = input_params or {}
    job_id = uuid.uuid4()
    estimate = estimate_job_credits(book, job_type)

    job = Job(
        id=job_id,
        book_id=book.id,
        user_id=user.id,
        type=job_type,
        status="queued",
        target_chapter_id=target_chapter_id,
        reserved_credits=estimate,
        input_params=input_params,
    )
    db.add(job)
    await db.flush()

    if charge:
        # Raises InsufficientCreditsError before any work begins.
        await credits_service.spend(
            db,
            user_id=user.id,
            amount=estimate,
            reason=CreditReason.GENERATION,
            description=f"{job_type.replace('_', ' ').title()} for '{book.title}'",
            job_id=job.id,
            book_id=book.id,
            idempotency_key=credits_service.charge_key(job.id),
        )
        job.charged = True
        book.credits_charged = (book.credits_charged or 0) + estimate

    await db.flush()
    log.info(
        "job_created",
        job_id=str(job.id),
        type=job_type,
        credits=estimate,
        book_id=str(book.id),
    )
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID, user: User) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job not found.", code="job_not_found")
    return job


async def enqueue(job: Job) -> None:
    """Dispatch a job according to ``JOB_EXECUTION_MODE``."""
    settings = get_settings()
    if settings.job_execution_mode == "arq":
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            if pool is not None:
                await pool.enqueue_job("run_job", str(job.id))
                log.info("job_enqueued_arq", job_id=str(job.id))
        except Exception as exc:  # noqa: BLE001 - fall back to inline so work isn't lost
            log.warning("arq_enqueue_failed_falling_back_inline", error=str(exc))
            _spawn_inline(job.id)
    else:
        _spawn_inline(job.id)


def _spawn_inline(job_id: uuid.UUID) -> None:
    task = asyncio.create_task(run_job(job_id))
    _inline_tasks.add(task)
    task.add_done_callback(_inline_tasks.discard)
    log.info("job_enqueued_inline", job_id=str(job_id))


async def run_job(job_id: uuid.UUID) -> str:
    """Execute a job in its own session. Used by both inline and arq modes."""
    from app.agents.orchestrator import Orchestrator
    from app.db.session import session_scope

    async with session_scope() as db:
        job = await db.get(Job, job_id)
        if job is None:
            log.warning("run_job_missing", job_id=str(job_id))
            return "missing"
        book = await db.get(Book, job.book_id)
        if book is None:
            job.status = "failed"
            job.error = "The book no longer exists."
            job.error_code = "book_not_found"
            await db.flush()
            return "failed"

        orchestrator = Orchestrator(db, job, book)
        await orchestrator.run()

        if job.status in ("failed", "cancelled"):
            await _maybe_refund(db, job, book)

        await _notify_completion(db, job, book)
        return job.status

    return "unknown"  # pragma: no cover


async def _maybe_refund(db: AsyncSession, job: Job, book: Book) -> None:
    """Refund a failed/cancelled job only if it produced no successful steps."""
    succeeded = await db.scalar(
        select(func.count())
        .select_from(AgentRun)
        .where(AgentRun.job_id == job.id, AgentRun.status == "succeeded")
    )
    if succeeded:
        log.info("job_failed_no_refund", job_id=str(job.id), successful_steps=int(succeeded))
        return
    amount = job.reserved_credits or 0
    if amount <= 0:
        return
    await credits_service.grant(
        db,
        user_id=job.user_id,
        amount=amount,
        reason=CreditReason.REFUND,
        description=f"Refund for failed job on '{book.title}'",
        idempotency_key=credits_service.refund_key(job.id, job.attempts),
    )
    job.charged = False
    log.info("job_refunded", job_id=str(job.id), credits=amount)


async def _notify_completion(db: AsyncSession, job: Job, book: Book) -> None:
    """Send the completion email for long jobs (best-effort)."""
    from app.services import email as email_service

    user = await db.get(User, job.user_id)
    if user is None:
        return
    subject, body = email_service.job_complete_email(book.title, job.status)
    try:
        await email_service.send_email(user.email, subject, body)
    except Exception as exc:  # noqa: BLE001
        log.warning("job_complete_email_failed", error=str(exc))


async def request_cancel(db: AsyncSession, job: Job) -> Job:
    if job.is_terminal:
        return job
    job.cancel_requested = True
    await db.flush()
    log.info("job_cancel_requested", job_id=str(job.id))
    return job


async def retry_job(db: AsyncSession, user: User, job: Job) -> Job:
    """Requeue a failed/cancelled job without charging again."""
    if job.status not in ("failed", "cancelled"):
        raise ConflictError(
            "Only failed or cancelled jobs can be retried.", code="job_not_retryable"
        )
    job.status = "queued"
    job.error = None
    job.error_code = None
    job.cancel_requested = False
    job.attempts = (job.attempts or 0) + 1
    job.finished_at = None
    # Do not touch completed_steps: the orchestrator resumes from there.
    await db.flush()
    if not job.charged and (job.reserved_credits or 0) > 0:
        await credits_service.spend(
            db,
            user_id=user.id,
            amount=job.reserved_credits,
            reason=CreditReason.GENERATION,
            description="Job retry",
            job_id=job.id,
            idempotency_key=credits_service.charge_key(job.id, job.attempts),
        )
        job.charged = True
    # Commit before the worker starts so the resumed state is observable.
    await db.commit()
    await enqueue(job)
    return job


async def list_jobs(
    db: AsyncSession,
    user: User,
    *,
    book_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Job], int]:
    conditions = [Job.user_id == user.id]
    if book_id:
        conditions.append(Job.book_id == book_id)
    total = await db.scalar(select(func.count()).select_from(Job).where(*conditions))
    result = await db.execute(
        select(Job).where(*conditions).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), int(total or 0)


async def list_agent_runs(db: AsyncSession, job_id: uuid.UUID) -> list[AgentRun]:
    result = await db.execute(
        select(AgentRun).where(AgentRun.job_id == job_id).order_by(AgentRun.created_at)
    )
    return list(result.scalars().all())


async def require_sufficient_credits(db: AsyncSession, user: User, amount: int) -> None:
    # Admins and VIP accounts have unlimited generation access
    if getattr(user, "is_admin", False) or getattr(user, "role", "") == "admin":
        return
    balance = await credits_service.get_balance(db, user.id)
    if balance < amount:
        raise InsufficientCreditsError(
            "Not enough credits for this generation.",
            details={"balance": balance, "required": amount},
        )


async def assert_book_generatable(book: Book, user: User | None = None) -> None:
    """Guard rails shared by generation endpoints."""
    if book.deleted_at is not None:
        raise AppError("This book was deleted.", code="book_deleted", status_code=409)
    # Admin / VIP accounts have no token budget ceiling
    if user and (getattr(user, "is_admin", False) or getattr(user, "role", "") == "admin"):
        return
    if (book.token_budget or 0) > 0 and (book.tokens_used or 0) >= (book.token_budget or 0):
        raise AppError(
            "This book has reached its token budget. Increase the budget to continue.",
            code="token_budget_exceeded",
            status_code=409,
        )


async def mark_stale_jobs_failed(db: AsyncSession, older_than_seconds: int = 3600) -> int:
    """Fail jobs stuck in ``running`` (e.g. after a worker crash)."""
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
    result = await db.execute(select(Job).where(Job.status == "running", Job.started_at < cutoff))
    count = 0
    for job in result.scalars().all():
        job.status = "failed"
        job.error_code = "stale_job"
        job.error = "The worker stopped before finishing. Retry to resume from the last good step."
        job.finished_at = datetime.now(UTC)
        count += 1
    if count:
        await db.flush()
    return count
