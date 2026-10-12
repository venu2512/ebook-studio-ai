"""Outline service: research + plan, persist, edit and approve.

The approved outline is what drives writing: approving it materialises one
``Chapter`` row per planned chapter, in order.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import PlannerAgent, ResearcherAgent
from app.agents.base import AgentContext, AgentResult
from app.agents.schemas import PlannerOutput, ResearchNoteOut
from app.core.errors import AppError, NotFoundError
from app.core.logging import get_logger
from app.db.models import Book, BookOutline, Chapter, ResearchNote

log = get_logger(__name__)


async def get_latest_outline(db: AsyncSession, book_id: object) -> BookOutline | None:
    result = await db.execute(
        select(BookOutline)
        .where(BookOutline.book_id == book_id)
        .order_by(BookOutline.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def require_outline(db: AsyncSession, book_id: object) -> BookOutline:
    outline = await get_latest_outline(db, book_id)
    if outline is None:
        raise NotFoundError("This book has no outline yet.", code="outline_not_found")
    return outline


async def save_research_notes(
    db: AsyncSession, book: Book, notes: list[ResearchNoteOut]
) -> list[ResearchNote]:
    """Replace the book's research notes with a fresh set."""
    await db.execute(delete(ResearchNote).where(ResearchNote.book_id == book.id))
    rows: list[ResearchNote] = []
    for note in notes:
        row = ResearchNote(
            book_id=book.id,
            query=note.query,
            finding=note.finding,
            source_url=note.source_url,
            source_title=note.source_title,
            confidence=note.confidence,
            is_verified=note.is_verified,
            tags=note.tags,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def load_research_notes(db: AsyncSession, book_id: object) -> list[ResearchNoteOut]:
    result = await db.execute(
        select(ResearchNote)
        .where(ResearchNote.book_id == book_id)
        .order_by(ResearchNote.created_at)
    )
    return [
        ResearchNoteOut(
            query=n.query,
            finding=n.finding,
            source_url=n.source_url,
            source_title=n.source_title,
            confidence=n.confidence,
            is_verified=n.is_verified,
            tags=n.tags or [],
        )
        for n in result.scalars().all()
    ]


async def run_research(ctx: AgentContext) -> AgentResult:
    """Run the researcher and return the full result (output + usage)."""
    return await _research_output(ctx)


async def _research_output(ctx: AgentContext) -> AgentResult:
    return await ResearcherAgent().run(ctx)


async def generate_outline(
    db: AsyncSession,
    book: Book,
    ctx: AgentContext,
    *,
    chapter_count: int | None = None,
    reuse_research: bool = True,
    persist_research: bool = True,
) -> tuple[BookOutline, AgentResult | None, AgentResult]:
    """Run Researcher (optional) + Planner and persist a new outline version."""
    research_result: AgentResult | None = None

    if reuse_research:
        existing = await load_research_notes(db, book.id)
        if existing:
            ctx.research_notes = existing

    if not ctx.research_notes:
        research_result = await _research_output(ctx)
        ctx.research_notes = research_result.output.notes  # type: ignore[attr-defined]
        if persist_research:
            await save_research_notes(db, book, research_result.output.notes)  # type: ignore[attr-defined]

    if chapter_count:
        ctx.target_chapter_count = chapter_count

    planner_result = await PlannerAgent().run(ctx)
    planner: PlannerOutput = planner_result.output  # type: ignore[assignment]

    version = (
        await db.scalar(
            select(func.coalesce(func.max(BookOutline.version), 0)).where(
                BookOutline.book_id == book.id
            )
        )
        or 0
    ) + 1

    outline = BookOutline(
        book_id=book.id,
        version=version,
        structure=planner.structure.model_dump(),
        total_word_budget=planner.total_word_budget
        or sum(c.word_budget for p in planner.structure.parts for c in p.chapters),
    )
    # Stash planner presentation fields alongside the structure for the UI.
    outline.structure = {
        **outline.structure,
        "title": planner.title,
        "subtitle": planner.subtitle,
        "title_options": planner.title_options,
        "reader_promise": planner.reader_promise,
    }
    db.add(outline)

    # Keep the draft title/subtitle in sync until the user overrides them.
    if not book.title or book.status == "draft":
        book.title = planner.title or book.title
    if planner.subtitle:
        book.subtitle = planner.subtitle
    book.status = "awaiting_approval"
    await db.flush()
    log.info("outline_generated", book_id=str(book.id), version=version)
    return outline, research_result, planner_result


async def update_outline(
    db: AsyncSession,
    outline: BookOutline,
    *,
    structure: dict[str, Any],
    title: str | None = None,
    subtitle: str | None = None,
    reader_promise: str | None = None,
) -> BookOutline:
    """Apply user edits to the outline structure."""
    merged = {**outline.structure, **structure}
    if title is not None:
        merged["title"] = title
    if subtitle is not None:
        merged["subtitle"] = subtitle
    if reader_promise is not None:
        merged["reader_promise"] = reader_promise
    outline.structure = merged
    outline.total_word_budget = sum(
        int(c.get("word_budget", 0))
        for part in merged.get("parts", [])
        for c in part.get("chapters", [])
    )
    await db.flush()
    return outline


def iter_planned_chapters(outline: BookOutline) -> list[tuple[str, dict[str, Any]]]:
    """Yield ``(part_title, chapter_dict)`` in order."""
    items: list[tuple[str, dict[str, Any]]] = []
    for part in outline.structure.get("parts", []):
        for chapter in part.get("chapters", []):
            items.append((part.get("title", "Part I"), chapter))
    return items


async def approve_outline(db: AsyncSession, book: Book, outline: BookOutline) -> list[Chapter]:
    """Approve the outline and materialise its chapters."""
    planned = iter_planned_chapters(outline)
    if not planned:
        raise AppError("The outline has no chapters to approve.", code="outline_empty")

    # Replace any previously planned chapters that were never generated.
    existing = await db.execute(select(Chapter).where(Chapter.book_id == book.id))
    for chapter in existing.scalars().all():
        if chapter.status == "pending":
            await db.delete(chapter)

    created: list[Chapter] = []
    for index, (part_title, plan) in enumerate(planned):
        chapter = Chapter(
            book_id=book.id,
            order_index=index,
            part_title=part_title,
            title=str(plan.get("title", f"Chapter {index + 1}"))[:400],
            summary=plan.get("summary", ""),
            key_points=list(plan.get("key_points", [])),
            target_word_count=int(plan.get("word_budget", 0)),
            status="pending",
        )
        db.add(chapter)
        created.append(chapter)

    outline.approved_at = datetime.now(UTC)
    book.status = "planning"
    await db.flush()
    log.info("outline_approved", book_id=str(book.id), chapters=len(created))
    return created
