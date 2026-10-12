"""Outline routes: generate, read, edit and approve."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.db.models import Book
from app.schemas.job import JobRead
from app.schemas.outline import (
    OutlineApprovalResponse,
    OutlineGenerateRequest,
    OutlineRead,
    OutlineUpdateRequest,
)
from app.services import books as books_service
from app.services import jobs as jobs_service
from app.services import outline as outline_service

router = APIRouter(prefix="/books/{book_id}/outline", tags=["outline"])


@router.post("", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def generate_outline(
    book_id: uuid.UUID,
    payload: OutlineGenerateRequest,
    user: CurrentUser,
    db: SessionDep,
) -> JobRead:
    """Start outline generation. Watch progress via the job SSE stream."""
    book: Book = await books_service.get_owned_book(db, book_id, user)
    await jobs_service.assert_book_generatable(book)
    job = await jobs_service.create_job(
        db,
        user,
        book,
        job_type="outline",
        input_params={
            "chapter_count": payload.chapter_count,
            "reuse_research": payload.reuse_research,
        },
    )
    await db.commit()
    await jobs_service.enqueue(job)
    return JobRead.model_validate(job)


@router.get("", response_model=OutlineRead)
async def get_outline(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> OutlineRead:
    await books_service.get_owned_book(db, book_id, user)
    outline = await outline_service.require_outline(db, book_id)
    return OutlineRead.model_validate(outline)


@router.patch("", response_model=OutlineRead)
async def update_outline(
    book_id: uuid.UUID, payload: OutlineUpdateRequest, user: CurrentUser, db: SessionDep
) -> OutlineRead:
    await books_service.get_owned_book(db, book_id, user)
    outline = await outline_service.require_outline(db, book_id)
    updated = await outline_service.update_outline(
        db,
        outline,
        structure=payload.structure,
        title=payload.title,
        subtitle=payload.subtitle,
        reader_promise=payload.reader_promise,
    )
    return OutlineRead.model_validate(updated)


@router.post("/approve", response_model=OutlineApprovalResponse)
async def approve_outline(
    book_id: uuid.UUID, user: CurrentUser, db: SessionDep
) -> OutlineApprovalResponse:
    """Approve the outline and materialise its chapters."""
    book = await books_service.get_owned_book(db, book_id, user)
    outline = await outline_service.require_outline(db, book_id)
    chapters = await outline_service.approve_outline(db, book, outline)
    return OutlineApprovalResponse(
        status=book.status,
        approved_at=outline.approved_at,
        chapter_count=len(chapters),
        total_word_budget=outline.total_word_budget,
    )
