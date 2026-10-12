"""Export routes: render a finished book to PDF/EPUB/DOCX and download it.

Rendering is synchronous here (it is fast and deterministic) so the user gets a
downloadable file immediately. Bulk generation goes through the job pipeline
(``POST /books/{id}/generate`` with ``type=export``) instead.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.db.models import Book, Export, Template
from app.schemas.common import MessageResponse, Page
from app.schemas.export import (
    ExportCreateRequest,
    ExportDownload,
    ExportRead,
    TemplateRead,
)
from app.services import books as books_service
from app.services import chapters as chapters_service
from app.services.exports import ExportService

router = APIRouter(tags=["exports"])

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(value: str) -> str:
    return _FILENAME_SAFE.sub("-", value).strip("-")[:80] or "book"


async def _get_owned_export(db, export_id: uuid.UUID, user) -> Export:
    result = await db.execute(
        select(Export).where(Export.id == export_id, Export.user_id == user.id)
    )
    export = result.scalar_one_or_none()
    if export is None:
        raise NotFoundError("Export not found.", code="export_not_found")
    return export


@router.post(
    "/books/{book_id}/exports",
    response_model=ExportRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_export(
    book_id: uuid.UUID, payload: ExportCreateRequest, user: CurrentUser, db: SessionDep
) -> ExportRead:
    """Render and store a single export format for a book."""
    book = await books_service.get_owned_book(db, book_id, user)
    chapters = await chapters_service.list_chapters(db, book_id)
    if not chapters:
        raise AppError(
            "Approve the outline and generate chapters before exporting.",
            code="no_chapters",
            status_code=409,
        )

    service = ExportService(db)
    try:
        export = await service.create_and_store(
            book,
            chapters,
            fmt=payload.format,
            template=payload.template,
            page_size=payload.page_size,
            include_front_matter=payload.include_front_matter,
            include_toc=payload.include_toc,
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(
            f"Export to {payload.format.upper()} failed: {exc}",
            code="export_failed",
            status_code=500,
        ) from exc
    return ExportRead.model_validate(export)


@router.get("/books/{book_id}/exports", response_model=Page[ExportRead])
async def list_exports(
    book_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    format: str | None = Query(default=None, pattern="^(pdf|epub|docx)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[ExportRead]:
    await books_service.get_owned_book(db, book_id, user)
    conditions = [Export.book_id == book_id, Export.user_id == user.id]
    if format:
        conditions.append(Export.format == format)
    result = await db.execute(
        select(Export)
        .where(*conditions)
        .order_by(Export.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [ExportRead.model_validate(e) for e in result.scalars().all()]
    return Page.build(items, len(items), limit, offset)


@router.get("/exports/{export_id}", response_model=ExportRead)
async def get_export(export_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ExportRead:
    export = await _get_owned_export(db, export_id, user)
    return ExportRead.model_validate(export)


@router.get("/exports/{export_id}/download", response_model=ExportDownload)
async def download_export(
    export_id: uuid.UUID, user: CurrentUser, db: SessionDep
) -> ExportDownload:
    """Return a short-lived signed download URL for an export."""
    export = await _get_owned_export(db, export_id, user)
    if export.status != "ready" or not export.storage_key:
        raise AppError(
            "This export is not ready to download.", code="export_not_ready", status_code=409
        )

    book = await db.get(Book, export.book_id)
    base = _slug(book.title if book else "book")
    filename = f"{base}.{export.format}"
    settings = get_settings()
    url = await ExportService(db).download_url(export, filename=filename)
    return ExportDownload(
        export_id=export.id,
        url=url,
        expires_in=settings.signed_url_expire_seconds,
        filename=filename,
        size_bytes=export.size_bytes,
    )


@router.post("/exports/{export_id}/download", response_model=ExportDownload)
async def download_export_post(
    export_id: uuid.UUID, user: CurrentUser, db: SessionDep
) -> ExportDownload:
    """POST variant so clients that cannot set query params still get a link."""
    return await download_export(export_id, user, db)


@router.delete("/exports/{export_id}", response_model=MessageResponse)
async def delete_export(export_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> MessageResponse:
    export = await _get_owned_export(db, export_id, user)
    await db.delete(export)
    return MessageResponse(message="Export deleted.")


@router.get("/templates", response_model=list[TemplateRead])
async def list_templates(
    user: CurrentUser,
    db: SessionDep,
    kind: str | None = Query(default=None, pattern="^(interior|cover)$"),
) -> list[TemplateRead]:
    """Available interior/cover templates for the wizard and export dialog."""
    conditions: list[Any] = [Template.is_active.is_(True)]
    if kind:
        conditions.append(Template.kind == kind)
    result = await db.execute(select(Template).where(*conditions).order_by(Template.name))
    return [TemplateRead.model_validate(t) for t in result.scalars().all()]
