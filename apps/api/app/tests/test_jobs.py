"""Job service: charging exactly once, retries, refunds and stale recovery."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import ConflictError, InsufficientCreditsError
from app.db.models import AgentRun, Book
from app.schemas.book import BookCreate
from app.services import books as books_service
from app.services import credits as credits_service
from app.services import jobs as jobs_service
from app.services import users as users_service


async def _user_and_book(db, *, credits: int = 100):
    user = await users_service.create_user(
        db, email=f"jobs-{uuid.uuid4().hex[:10]}@example.com", password="password123"
    )
    user.credits_balance = credits
    await db.flush()
    book = await books_service.create_book(
        db, user, BookCreate(topic="A practical topic", target_pages=6, chapter_count=3)
    )
    return user, book


def test_estimate_job_credits_uses_cost_factors():
    book = Book(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="t",
        topic="topic",
        estimated_credits=100,
    )
    assert jobs_service.estimate_job_credits(book, "full_book") == 100
    assert jobs_service.estimate_job_credits(book, "outline") == 15
    assert jobs_service.estimate_job_credits(book, "chapter") == 12
    assert jobs_service.estimate_job_credits(book, "export") == 1
    # Unknown job types fall back to a small fraction.
    assert jobs_service.estimate_job_credits(book, "mystery") == 10


async def test_create_job_charges_exactly_once(db):
    user, book = await _user_and_book(db, credits=100)
    job = await jobs_service.create_job(db, user, book, job_type="outline")

    expected = jobs_service.estimate_job_credits(book, "outline")
    assert job.charged is True
    assert job.reserved_credits == expected
    balance = await credits_service.get_balance(db, user.id)
    assert balance == 100 - expected
    assert balance == await credits_service.ledger_sum(db, user.id)

    # Re-running the same logical charge with the job key is a no-op.
    dup = await credits_service.spend(
        db,
        user_id=user.id,
        amount=expected,
        idempotency_key=credits_service.charge_key(job.id),
    )
    assert dup is None
    assert await credits_service.get_balance(db, user.id) == balance


async def test_create_job_without_credits_raises(db):
    user, book = await _user_and_book(db, credits=0)
    with pytest.raises(InsufficientCreditsError):
        await jobs_service.create_job(db, user, book, job_type="full_book")


async def test_retry_does_not_recharge_and_resumes(db, monkeypatch):
    user, book = await _user_and_book(db, credits=100)
    job = await jobs_service.create_job(db, user, book, job_type="outline")
    balance_after_first_charge = await credits_service.get_balance(db, user.id)

    # Simulate a mid-pipeline failure after the research step completed.
    job.status = "failed"
    job.error = "boom"
    job.error_code = "job_failed"
    job.completed_steps = ["research"]
    await db.flush()

    enqueued: list[str] = []

    async def _fake_enqueue(_job):
        enqueued.append(str(_job.id))

    monkeypatch.setattr(jobs_service, "enqueue", _fake_enqueue)

    retried = await jobs_service.retry_job(db, user, job)
    assert retried.status == "queued"
    assert retried.attempts == 1
    assert retried.completed_steps == ["research"]  # resume point preserved
    assert retried.charged is True
    # No second charge.
    assert await credits_service.get_balance(db, user.id) == balance_after_first_charge
    assert enqueued == [str(job.id)]


async def test_retry_recharges_a_refunded_job(db, monkeypatch):
    user, book = await _user_and_book(db, credits=100)
    job = await jobs_service.create_job(db, user, book, job_type="outline")
    reserved = job.reserved_credits

    # A failed job with no successful runs gets refunded.
    job.status = "failed"
    await jobs_service._maybe_refund(db, job, book)
    assert job.charged is False
    assert await credits_service.get_balance(db, user.id) == 100

    async def _fake_enqueue(_job):
        return None

    monkeypatch.setattr(jobs_service, "enqueue", _fake_enqueue)
    await jobs_service.retry_job(db, user, job)

    # The retry charges the reserved amount back, exactly once.
    assert job.charged is True
    assert await credits_service.get_balance(db, user.id) == 100 - reserved


async def test_only_failed_or_cancelled_jobs_can_be_retried(db, monkeypatch):
    user, book = await _user_and_book(db)
    job = await jobs_service.create_job(db, user, book, job_type="outline")
    job.status = "succeeded"

    async def _fake_enqueue(_job):
        return None

    monkeypatch.setattr(jobs_service, "enqueue", _fake_enqueue)
    with pytest.raises(ConflictError):
        await jobs_service.retry_job(db, user, job)


async def test_refund_skipped_when_a_step_succeeded(db):
    user, book = await _user_and_book(db, credits=100)
    job = await jobs_service.create_job(db, user, book, job_type="outline")
    balance_after_charge = await credits_service.get_balance(db, user.id)

    db.add(
        AgentRun(
            job_id=job.id,
            book_id=book.id,
            agent_name="planner",
            input_hash="deadbeef",
            step_key="plan",
            status="succeeded",
        )
    )
    await db.flush()

    job.status = "failed"
    await jobs_service._maybe_refund(db, job, book)
    # A job that produced output is not refunded.
    assert job.charged is True
    assert await credits_service.get_balance(db, user.id) == balance_after_charge


async def test_refund_is_idempotent(db):
    user, book = await _user_and_book(db, credits=100)
    job = await jobs_service.create_job(db, user, book, job_type="outline")
    job.status = "failed"

    await jobs_service._maybe_refund(db, job, book)
    await jobs_service._maybe_refund(db, job, book)  # second call must not double-refund
    assert await credits_service.get_balance(db, user.id) == 100


async def test_cancel_request_sets_flag(db):
    user, book = await _user_and_book(db)
    job = await jobs_service.create_job(db, user, book, job_type="outline")
    await jobs_service.request_cancel(db, job)
    assert job.cancel_requested is True


async def test_mark_stale_jobs_failed(db):
    user, book = await _user_and_book(db)
    job = await jobs_service.create_job(db, user, book, job_type="outline")
    job.status = "running"
    job.started_at = datetime.now(UTC) - timedelta(hours=3)
    await db.flush()

    count = await jobs_service.mark_stale_jobs_failed(db, older_than_seconds=3600)
    assert count == 1
    assert job.status == "failed"
    assert job.error_code == "stale_job"


async def test_assert_book_generatable_rejects_deleted_and_over_budget(db):
    _user, book = await _user_and_book(db)

    from app.core.errors import AppError

    book.tokens_used = book.token_budget
    with pytest.raises(AppError) as exc:
        await jobs_service.assert_book_generatable(book)
    assert exc.value.code == "token_budget_exceeded"

    book.tokens_used = 0
    book.deleted_at = datetime.now(UTC)
    with pytest.raises(AppError) as exc:
        await jobs_service.assert_book_generatable(book)
    assert exc.value.code == "book_deleted"


async def test_list_jobs_filters_by_book(db):
    user, book = await _user_and_book(db)
    await jobs_service.create_job(db, user, book, job_type="outline")
    await jobs_service.create_job(db, user, book, job_type="full_book")
    items, total = await jobs_service.list_jobs(db, user, book_id=book.id)
    assert total == 2
    assert all(j.book_id == book.id for j in items)


async def test_get_job_enforces_ownership(db):
    user, book = await _user_and_book(db)
    job = await jobs_service.create_job(db, user, book, job_type="outline")

    other = await users_service.create_user(
        db, email=f"other-{uuid.uuid4().hex[:10]}@example.com", password="password123"
    )
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        await jobs_service.get_job(db, job.id, other)
    # The owner can fetch it.
    assert (await jobs_service.get_job(db, job.id, user)).id == job.id


def test_cost_factors_are_all_positive():
    assert all(v > 0 for v in jobs_service.COST_FACTORS.values())
    assert jobs_service.COST_FACTORS["full_book"] == 1.0
