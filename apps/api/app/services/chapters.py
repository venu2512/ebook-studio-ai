"""Chapter service: editing with version history, AI actions and restoration."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.db.models import Book, Chapter, ChapterVersion
from app.llm.base import LLMMessage
from app.llm.factory import get_llm_client
from app.schemas.chapter import AIActionRequest, ChapterUpdate

log = get_logger(__name__)


def word_count(text: str | None) -> int:
    return len(re.findall(r"\S+", text or ""))


async def list_chapters(db: AsyncSession, book_id: uuid.UUID) -> list[Chapter]:
    result = await db.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.order_index)
    )
    return list(result.scalars().all())


async def get_chapter(db: AsyncSession, book_id: uuid.UUID, chapter_id: uuid.UUID) -> Chapter:
    result = await db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.book_id == book_id)
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    return chapter


async def create_version(
    db: AsyncSession,
    chapter: Chapter,
    *,
    content: str,
    source: str = "agent",
    editor_notes: str | None = None,
) -> ChapterVersion:
    """Append an immutable snapshot and bump the chapter's current version."""
    chapter.current_version += 1
    version = ChapterVersion(
        chapter_id=chapter.id,
        version=chapter.current_version,
        content=content,
        word_count=word_count(content),
        source=source,
        editor_notes=editor_notes,
    )
    db.add(version)
    await db.flush()
    return version


async def update_chapter(
    db: AsyncSession, chapter: Chapter, payload: ChapterUpdate, *, source: str = "user"
) -> Chapter:
    """Save editor changes, optionally snapshotting a new version."""
    if payload.title is not None:
        chapter.title = payload.title
    if payload.summary is not None:
        chapter.summary = payload.summary
    if payload.status is not None:
        chapter.status = payload.status

    if payload.content is not None and payload.content != chapter.content:
        chapter.content = payload.content
        chapter.word_count = word_count(payload.content)
        if payload.create_version:
            await create_version(
                db,
                chapter,
                content=payload.content,
                source=source,
                editor_notes=payload.editor_notes,
            )
    await db.flush()
    return chapter


async def list_versions(
    db: AsyncSession, chapter_id: uuid.UUID, *, limit: int = 50, offset: int = 0
) -> tuple[list[ChapterVersion], int]:
    total = await db.scalar(
        select(func.count())
        .select_from(ChapterVersion)
        .where(ChapterVersion.chapter_id == chapter_id)
    )
    result = await db.execute(
        select(ChapterVersion)
        .where(ChapterVersion.chapter_id == chapter_id)
        .order_by(ChapterVersion.version.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), int(total or 0)


async def get_version(db: AsyncSession, chapter: Chapter, version: int) -> ChapterVersion:
    result = await db.execute(
        select(ChapterVersion).where(
            ChapterVersion.chapter_id == chapter.id, ChapterVersion.version == version
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Chapter version not found.", code="version_not_found")
    return row


async def restore_version(db: AsyncSession, chapter: Chapter, version: int) -> Chapter:
    """Restore a previous version as a brand-new version (non-destructive)."""
    snapshot = await get_version(db, chapter, version)
    chapter.content = snapshot.content
    chapter.word_count = snapshot.word_count
    await create_version(
        db,
        chapter,
        content=snapshot.content,
        source="restore",
        editor_notes=f"Restored from version {version}",
    )
    await db.flush()
    log.info("chapter_restored", chapter_id=str(chapter.id), version=version)
    return chapter


# ---------------------------------------------------------------------------
# Inline AI actions (rewrite / expand / shorten / change tone)
# ---------------------------------------------------------------------------
ACTION_INSTRUCTIONS: dict[str, str] = {
    "rewrite": "Rewrite the passage to be clearer and more engaging while keeping the meaning.",
    "expand": "Expand the passage with more depth, examples and explanation.",
    "shorten": "Tighten the passage, removing repetition and filler, keeping all key ideas.",
    "change_tone": "Rewrite the passage in the requested tone, keeping the meaning and facts.",
    "improve": "Improve grammar, flow and readability without changing the substance.",
}


async def apply_ai_action(
    db: AsyncSession,
    *,
    book: Book,
    chapter: Chapter,
    payload: AIActionRequest,
) -> tuple[str, list[dict[str, Any]]]:
    """Run an inline editor action. Returns ``(new_markdown, flags)``."""
    if payload.action not in ACTION_INSTRUCTIONS:
        raise ValidationAppError("Unknown AI action.", details={"action": payload.action})

    target = payload.selection or chapter.content or ""
    if not target.strip():
        raise ValidationAppError("There is no content to edit.")

    instruction = ACTION_INSTRUCTIONS[payload.action]
    if payload.action == "change_tone" and payload.tone:
        instruction += f" Target tone: {payload.tone}."
    if payload.instructions:
        instruction += f" Additional instruction: {payload.instructions}"

    from app.core.config import get_settings

    settings = get_settings()
    llm = get_llm_client()
    messages = [
        LLMMessage(
            role="system",
            content=(
                "You are a precise book editor. Never invent facts, statistics or quotes. "
                "Return only the edited Markdown, with no preamble or code fences."
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                f"Book: {book.title}\nAudience: {book.audience}\nTone: {book.tone}\n\n"
                f"{instruction}\n\n<passage>\n{target}\n</passage>"
            ),
        ),
    ]
    response = await llm.complete(
        messages,
        model=settings.model_for_agent("editor"),
        temperature=0.5,
        task=f"ai_action.{payload.action}",
        mock_payload={"markdown": target, "chapter_title": chapter.title},
    )
    new_content = _strip_fences(response.content)

    # Selecting a passage means a partial replacement.
    if payload.selection and chapter.content:
        new_content = chapter.content.replace(payload.selection, new_content, 1)

    flags: list[dict[str, Any]] = []
    if _looks_like_unverified_claim(new_content):
        flags.append(
            {
                "type": "unverified_claim",
                "message": "This passage may contain an unsourced claim. Verify before export.",
            }
        )
    return new_content, flags


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


_CLAIM_PATTERNS = (
    "studies show",
    "research shows",
    "according to a study",
    "scientists found",
    "percent of",
    "% of",
)


def _looks_like_unverified_claim(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in _CLAIM_PATTERNS)


def build_style_guide(book: Book) -> str:
    """Compose the effective style guide for the Writer/Editor agents."""
    if book.style_guide:
        return book.style_guide
    return (
        f"Write for {book.audience} in a {book.tone} tone. Use plain language, "
        "short paragraphs, concrete examples and second person. End every chapter "
        "with a short 'Key takeaways' list. Never fabricate statistics or quotes."
    )
