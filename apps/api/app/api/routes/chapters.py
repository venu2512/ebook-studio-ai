"""Chapter routes: list, edit, AI actions, regenerate, version history."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas.chapter import (
    AIActionRequest,
    AIActionResponse,
    ChapterListItem,
    ChapterRead,
    ChapterRegenerateRequest,
    ChapterRestoreRequest,
    ChapterUpdate,
    ChapterVersionDetail,
    ChapterVersionRead,
)
from app.schemas.common import Page
from app.schemas.job import JobRead
from app.services import books as books_service
from app.services import chapters as chapters_service
from app.services import jobs as jobs_service

router = APIRouter(tags=["chapters"])


@router.get("/books/{book_id}/chapters", response_model=Page[ChapterListItem])
async def list_chapters(
    book_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[ChapterListItem]:
    await books_service.get_owned_book(db, book_id, user)
    chapters = await chapters_service.list_chapters(db, book_id)
    items = [ChapterListItem.model_validate(c) for c in chapters]
    return Page.build(items[offset : offset + limit], len(items), limit, offset)


@router.get("/chapters/{chapter_id}", response_model=ChapterRead)
async def get_chapter(chapter_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ChapterRead:
    from app.db.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    await books_service.get_owned_book(db, chapter.book_id, user)
    return ChapterRead.model_validate(chapter)


@router.patch("/chapters/{chapter_id}", response_model=ChapterRead)
async def update_chapter(
    chapter_id: uuid.UUID, payload: ChapterUpdate, user: CurrentUser, db: SessionDep
) -> ChapterRead:
    from app.db.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    await books_service.get_owned_book(db, chapter.book_id, user)
    updated = await chapters_service.update_chapter(db, chapter, payload)
    return ChapterRead.model_validate(updated)


@router.post("/chapters/{chapter_id}/ai-action", response_model=AIActionResponse)
async def ai_action(
    chapter_id: uuid.UUID, payload: AIActionRequest, user: CurrentUser, db: SessionDep
) -> AIActionResponse:
    """Inline editor actions: rewrite, expand, shorten, change tone, improve."""
    from app.db.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    book = await books_service.get_owned_book(db, chapter.book_id, user)
    content, flags = await chapters_service.apply_ai_action(
        db, book=book, chapter=chapter, payload=payload
    )
    return AIActionResponse(
        chapter_id=chapter.id,
        action=payload.action,
        content=content,
        word_count=chapters_service.word_count(content),
        flags=flags,
    )


@router.post("/chapters/{chapter_id}/regenerate", response_model=JobRead, status_code=202)
async def regenerate_chapter(
    chapter_id: uuid.UUID,
    payload: ChapterRegenerateRequest,
    user: CurrentUser,
    db: SessionDep,
) -> JobRead:
    from app.db.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    book = await books_service.get_owned_book(db, chapter.book_id, user)
    await jobs_service.assert_book_generatable(book)
    job = await jobs_service.create_job(
        db,
        user,
        book,
        job_type="chapter",
        target_chapter_id=chapter.id,
        input_params={"instructions": payload.instructions, "chapter_id": str(chapter.id)},
    )
    await db.commit()
    await jobs_service.enqueue(job)
    return JobRead.model_validate(job)


@router.get("/chapters/{chapter_id}/versions", response_model=Page[ChapterVersionRead])
async def list_versions(
    chapter_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[ChapterVersionRead]:
    from app.db.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    await books_service.get_owned_book(db, chapter.book_id, user)
    versions, total = await chapters_service.list_versions(
        db, chapter_id, limit=limit, offset=offset
    )
    return Page.build(
        [ChapterVersionRead.model_validate(v) for v in versions], total, limit, offset
    )


@router.get("/chapters/{chapter_id}/versions/{version}", response_model=ChapterVersionDetail)
async def get_version(
    chapter_id: uuid.UUID, version: int, user: CurrentUser, db: SessionDep
) -> ChapterVersionDetail:
    from app.db.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    await books_service.get_owned_book(db, chapter.book_id, user)
    snapshot = await chapters_service.get_version(db, chapter, version)
    return ChapterVersionDetail.model_validate(snapshot)


@router.post("/chapters/{chapter_id}/restore", response_model=ChapterRead)
async def restore_version(
    chapter_id: uuid.UUID, payload: ChapterRestoreRequest, user: CurrentUser, db: SessionDep
) -> ChapterRead:
    from app.db.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Chapter not found.", code="chapter_not_found")
    await books_service.get_owned_book(db, chapter.book_id, user)
    updated = await chapters_service.restore_version(db, chapter, payload.version)
    return ChapterRead.model_validate(updated)
