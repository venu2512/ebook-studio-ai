"""Book CRUD and cost estimation routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.db.models import Book
from app.schemas.book import (
    BookCreate,
    BookRead,
    BookUpdate,
    BookWithProgress,
    CostEstimate,
)
from app.schemas.common import MessageResponse, Page
from app.services import books as books_service
from app.services import credits as credits_service

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(payload: BookCreate, user: CurrentUser, db: SessionDep) -> BookRead:
    """Create a book from the wizard payload."""
    book = await books_service.create_book(db, user, payload)
    return BookRead.model_validate(book)


@router.get("", response_model=Page[BookWithProgress])
async def list_books(
    user: CurrentUser,
    db: SessionDep,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[BookWithProgress]:
    books, total = await books_service.list_books(
        db, user, status=status_filter, search=search, limit=limit, offset=offset
    )
    stats = await books_service.chapter_stats(db, [b.id for b in books])
    items: list[BookWithProgress] = []
    for book in books:
        total_ch, done_ch = stats.get(book.id, (0, 0))
        job = await books_service.latest_job(db, book.id)
        progress = int(done_ch / total_ch * 100) if total_ch else 0
        item = BookWithProgress.model_validate(book)
        item.chapter_count = total_ch
        item.completed_chapters = done_ch
        item.progress_pct = progress
        item.current_job_status = job.status if job else None
        items.append(item)
    return Page.build(items, total, limit, offset)


@router.get("/{book_id}", response_model=BookRead)
async def get_book(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> BookRead:
    book = await books_service.get_owned_book(db, book_id, user)
    return BookRead.model_validate(book)


@router.patch("/{book_id}", response_model=BookRead)
async def update_book(
    book_id: uuid.UUID, payload: BookUpdate, user: CurrentUser, db: SessionDep
) -> BookRead:
    book = await books_service.get_owned_book(db, book_id, user)
    updated = await books_service.update_book(db, book, payload)
    return BookRead.model_validate(updated)


@router.delete("/{book_id}", response_model=MessageResponse)
async def delete_book(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> MessageResponse:
    """Soft-delete a book (recoverable)."""
    book = await books_service.get_owned_book(db, book_id, user)
    await books_service.soft_delete_book(db, book)
    return MessageResponse(message="Book deleted.")


@router.get("/{book_id}/cost-estimate", response_model=CostEstimate)
async def cost_estimate(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> CostEstimate:
    """Estimated tokens/credits before a full generation run."""
    book = await books_service.get_owned_book(db, book_id, user)
    chapter_count = (book.metadata_json or {}).get("chapter_count") or max(
        5, book.target_pages // 3
    )
    tokens, credits = credits_service.estimate_book_credits(book.target_word_count, chapter_count)
    settings = get_settings()
    return CostEstimate(
        estimated_tokens=tokens,
        estimated_credits=credits,
        user_balance=user.credits_balance,
        affordable=user.credits_balance >= credits,
        breakdown={
            "chapters": int(chapter_count),
            "words": int(book.target_word_count),
            "credits_per_1k_tokens": int(settings.credits_per_1k_tokens),
            "token_budget": int(book.token_budget),
        },
    )


@router.get("/{book_id}/bible", response_model=dict)
async def get_bible(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> dict:
    """The running book bible shared with every Writer call."""
    book: Book = await books_service.get_owned_book(db, book_id, user)
    ctx = books_service.build_agent_context(book)
    return ctx.bible.model_dump()
