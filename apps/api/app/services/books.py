"""Book service: CRUD, ownership checks and agent-context construction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.schemas import BookBible
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.db.models import Book, Chapter, Job, User
from app.schemas.book import BookCreate, BookUpdate
from app.services.credits import estimate_book_credits

log = get_logger(__name__)


async def create_book(db: AsyncSession, user: User, payload: BookCreate) -> Book:
    chapter_count = payload.chapter_count or max(5, payload.target_pages // 3)
    word_count = payload.target_word_count or payload.target_pages * 250
    tokens, credits = estimate_book_credits(word_count, chapter_count)
    from app.core.config import get_settings

    settings = get_settings()
    book = Book(
        user_id=user.id,
        title=payload.title or payload.topic[:120],
        topic=payload.topic,
        audience=payload.audience,
        category=payload.category,
        language=payload.language,
        tone=payload.tone,
        style_guide=payload.style_guide,
        author_name=payload.author_name,
        target_pages=payload.target_pages,
        target_word_count=word_count,
        keywords=payload.keywords or [],
        status="draft",
        estimated_credits=credits,
        token_budget=min(settings.default_book_token_budget, max(tokens * 2, 20_000)),
        metadata_json={"template": payload.template, "chapter_count": chapter_count},
        bible={},
    )
    db.add(book)
    await db.flush()
    log.info("book_created", book_id=str(book.id), user_id=str(user.id))
    return book


async def get_owned_book(db: AsyncSession, book_id: uuid.UUID, user: User) -> Book:
    """Fetch a book the user owns, or raise 404 (never leak existence)."""
    result = await db.execute(
        select(Book).where(
            Book.id == book_id,
            Book.user_id == user.id,
            Book.deleted_at.is_(None),
        )
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise NotFoundError("Book not found.", code="book_not_found")
    return book


async def list_books(
    db: AsyncSession,
    user: User,
    *,
    status: str | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Book], int]:
    conditions = [Book.user_id == user.id, Book.deleted_at.is_(None)]
    if status:
        conditions.append(Book.status == status)
    if search:
        like = f"%{search.lower()}%"
        conditions.append(or_(func.lower(Book.title).like(like), func.lower(Book.topic).like(like)))

    total = await db.scalar(select(func.count()).select_from(Book).where(*conditions))
    result = await db.execute(
        select(Book).where(*conditions).order_by(Book.updated_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), int(total or 0)


async def chapter_stats(
    db: AsyncSession, book_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, int]]:
    """Return ``{book_id: (total_chapters, completed_chapters)}``."""
    if not book_ids:
        return {}
    result = await db.execute(
        select(Chapter.book_id, func.count(Chapter.id))
        .where(Chapter.book_id.in_(book_ids))
        .group_by(Chapter.book_id)
    )
    totals = {row[0]: int(row[1]) for row in result.all()}

    done_result = await db.execute(
        select(Chapter.book_id, func.count(Chapter.id))
        .where(
            Chapter.book_id.in_(book_ids),
            Chapter.status.in_(["fact_checked", "approved", "edited", "drafted"]),
        )
        .group_by(Chapter.book_id)
    )
    done = {row[0]: int(row[1]) for row in done_result.all()}
    return {bid: (totals.get(bid, 0), done.get(bid, 0)) for bid in book_ids}


async def latest_job(db: AsyncSession, book_id: uuid.UUID) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.book_id == book_id).order_by(Job.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def update_book(db: AsyncSession, book: Book, payload: BookUpdate) -> Book:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(book, key, value)
    if payload.target_pages and not payload.target_word_count:
        book.target_word_count = payload.target_pages * 250
    await db.flush()
    return book


async def soft_delete_book(db: AsyncSession, book: Book) -> None:
    book.deleted_at = datetime.now(UTC)
    book.status = "cancelled"
    await db.flush()
    log.info("book_soft_deleted", book_id=str(book.id))


async def restore_book(db: AsyncSession, book: Book) -> Book:
    book.deleted_at = None
    await db.flush()
    return book


def build_agent_context(book: Book) -> AgentContext:
    """Assemble the agent context (brief + running book bible)."""
    bible_data = book.bible or {}
    bible = BookBible(
        audience=book.audience,
        language=book.language,
        tone=book.tone,
        style_guide=book.style_guide or "",
        terminology=bible_data.get("terminology", {}) or {},
        chapter_summaries=bible_data.get("chapter_summaries", []) or [],
        must_include=bible_data.get("must_include", []) or [],
        must_avoid=bible_data.get("must_avoid", []) or [],
    )
    chapter_count = (book.metadata_json or {}).get("chapter_count") or max(
        5, book.target_pages // 3
    )
    return AgentContext(
        book_id=book.id,
        user_id=book.user_id,
        job_id=None,
        title=book.title,
        topic=book.topic,
        audience=book.audience,
        category=book.category,
        language=book.language,
        tone=book.tone,
        style_guide=book.style_guide or "",
        target_word_count=book.target_word_count,
        target_chapter_count=chapter_count,
        author_name=book.author_name or "",
        bible=bible,
        is_sensitive=book.is_sensitive,
        extra={"keywords": book.keywords or []},
    )
