"""Pipeline resumability: completed steps are skipped on a resumed run."""

from __future__ import annotations

import uuid

from app.agents.orchestrator import Orchestrator
from app.db.models import Job
from app.schemas.book import BookCreate
from app.services import books as books_service
from app.services import jobs as jobs_service
from app.services import outline as outline_service
from app.services import users as users_service


async def _prepared_book(db):
    """Create a book with an approved 3-chapter outline and a generous budget."""
    user = await users_service.create_user(
        db, email=f"resume-{uuid.uuid4().hex[:10]}@example.com", password="password123"
    )
    book = await books_service.create_book(
        db, user, BookCreate(topic="Resumable pipeline", target_pages=6, chapter_count=3)
    )
    # Keep this test focused on resume semantics, not on budget arithmetic.
    book.token_budget = 5_000_000
    await db.flush()

    ctx = books_service.build_agent_context(book)
    outline, _, _ = await outline_service.generate_outline(db, book, ctx, chapter_count=3)
    await outline_service.approve_outline(db, book, outline)
    await db.flush()
    return user, book


async def test_orchestrator_skips_completed_steps_on_resume(db):
    user, book = await _prepared_book(db)

    first = Job(book_id=book.id, user_id=user.id, type="full_book", status="queued")
    db.add(first)
    await db.flush()
    await Orchestrator(db, first, book).run()
    assert first.status == "succeeded"

    first_keys = {r.step_key for r in await jobs_service.list_agent_runs(db, first.id)}
    assert {"writer:0", "editor:0", "fact:0", "design", "publish", "marketing"} <= first_keys

    # Resume a fresh job that already records chapter 0 as done.
    resumed = Job(
        book_id=book.id,
        user_id=user.id,
        type="full_book",
        status="queued",
        completed_steps=["writer:0", "editor:0", "fact:0"],
    )
    db.add(resumed)
    await db.flush()
    await Orchestrator(db, resumed, book).run()
    assert resumed.status == "succeeded"

    resumed_keys = {r.step_key for r in await jobs_service.list_agent_runs(db, resumed.id)}
    # Chapter 0 is not regenerated...
    assert {"writer:0", "editor:0", "fact:0"}.isdisjoint(resumed_keys)
    # ...but later chapters are.
    assert "writer:1" in resumed_keys


async def test_orchestrator_honours_cancel_request(db):
    user, book = await _prepared_book(db)
    job = Job(
        book_id=book.id,
        user_id=user.id,
        type="full_book",
        status="queued",
        cancel_requested=True,
    )
    db.add(job)
    await db.flush()
    await Orchestrator(db, job, book).run()
    assert job.status == "cancelled"
    assert job.error


async def test_orchestrator_records_progress_and_tokens(db):
    user, book = await _prepared_book(db)
    job = Job(book_id=book.id, user_id=user.id, type="outline", status="queued")
    db.add(job)
    await db.flush()
    await Orchestrator(db, job, book).run()

    assert job.status == "succeeded"
    assert job.progress_pct == 100
    assert job.current_step is None
    assert book.status == "awaiting_approval"
    assert book.tokens_used > 0  # usage is folded into the book totals
    runs = await jobs_service.list_agent_runs(db, job.id)
    assert runs  # research + plan audit rows exist
    assert all(r.input_hash for r in runs)
