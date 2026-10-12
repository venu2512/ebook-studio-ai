"""Export service: renders a book to PDF/EPUB/DOCX, validates and stores it.

Implements the ``BookExporter`` protocol the Publisher agent depends on, so the
agent stays free of database access while this service owns persistence.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import PublishedArtifact
from app.core.errors import AppError
from app.core.logging import get_logger
from app.db.models import Asset, Book, Export
from app.services import documents as docs
from app.services.storage import checksum, get_storage, guess_content_type

log = get_logger(__name__)

WORDS_PER_PAGE = 300

MIME = {
    "pdf": "application/pdf",
    "epub": "application/epub+zip",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def storage_key(book_id: uuid.UUID, fmt: str, template: str, *, version: int = 0) -> str:
    return f"exports/{book_id}/{template}-{fmt}-v{version}.{fmt}"


async def load_cover_bytes(db: AsyncSession, book: Book) -> tuple[bytes | None, str]:
    """Load the book's cover image bytes, if any."""
    if not book.cover_asset_id:
        return None, "image/png"
    result = await db.execute(select(Asset).where(Asset.id == book.cover_asset_id))
    asset = result.scalar_one_or_none()
    if asset is None:
        return None, "image/png"
    try:
        data = await get_storage().get_bytes(asset.storage_key)
        return data, asset.mime_type or "image/png"
    except Exception as exc:  # noqa: BLE001 - cover is optional
        log.warning("cover_load_failed", asset_id=str(asset.id), error=str(exc))
        return None, "image/png"


async def build_document(
    db: AsyncSession,
    book: Book,
    chapters: list[Any],
    *,
    template: str = "classic",
    page_size: str = "a5",
    include_front_matter: bool = True,
    include_toc: bool = True,
    author_bio: str | None = None,
    palette: dict[str, str] | None = None,
) -> docs.BookDocument:
    cover_bytes, cover_mime = await load_cover_bytes(db, book)
    document = docs.assemble_document(
        book=book,
        chapters=chapters,
        template=template,
        page_size=page_size,
        include_front_matter=include_front_matter,
        include_toc=include_toc,
        author_bio=author_bio,
        palette=palette,
        cover_image_bytes=cover_bytes,
    )
    document.cover_mime = cover_mime
    return document


def validate_export(data: bytes, fmt: str, document: docs.BookDocument) -> dict[str, Any]:
    """Per-format validation report."""
    report: dict[str, Any] = {"format": fmt, "ok": True, "checks": {}}
    if fmt == "epub":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                report["checks"]["mimetype"] = "mimetype" in names
                report["checks"]["container"] = "META-INF/container.xml" in names
                report["checks"]["nav"] = any("nav" in n for n in names)
                report["ok"] = (
                    report["checks"]["mimetype"]
                    and report["checks"]["container"]
                    and report["checks"]["nav"]
                )
        except zipfile.BadZipFile:
            report["ok"] = False
            report["checks"]["zip"] = False
    elif fmt == "pdf":
        report["checks"]["header"] = data[:5] == b"%PDF-"
        report["checks"]["eof"] = b"%%EOF" in data[-2048:]
        # Embedded images: a PDF with a cover contains an XObject stream.
        report["checks"]["has_images"] = b"/Image" in data
        report["ok"] = report["checks"]["header"] and report["checks"]["eof"]
    elif fmt == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                report["checks"]["document"] = "word/document.xml" in names
                report["checks"]["content_types"] = "[Content_Types].xml" in names
                report["ok"] = report["checks"]["document"] and report["checks"]["content_types"]
        except zipfile.BadZipFile:
            report["ok"] = False
    report["chapter_count"] = len(document.chapters)
    report["word_count"] = document.total_word_count
    report["empty_chapters"] = [c.title for c in document.chapters if not c.markdown.strip()]
    return report


def estimate_pages(document: docs.BookDocument) -> int:
    return max(1, round(document.total_word_count / WORDS_PER_PAGE))


class ExportService:
    """Renders documents and persists :class:`Export` rows + objects."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def render(
        self, document: docs.BookDocument, fmt: str, *, template: str = "classic"
    ) -> PublishedArtifact:
        """Render, validate, store and record an export. Used by the Publisher."""
        return await self.render_and_store(document, fmt, template=template)

    async def render_and_store(
        self,
        document: docs.BookDocument,
        fmt: str,
        *,
        template: str = "classic",
        book: Book | None = None,
        create_record: bool = True,
    ) -> PublishedArtifact:
        data, renderer = docs.render(document, fmt)
        report = validate_export(data, fmt, document)
        page_count = estimate_pages(document) if fmt == "pdf" else None
        digest = checksum(data)

        book_id = document.book_id
        if book_id is None:
            raise AppError(
                "Cannot store an export without an associated book.",
                code="export_missing_book",
                status_code=409,
            )
        key = storage_key(book_id, fmt, template)
        await get_storage().put_bytes(key, data, MIME.get(fmt, guess_content_type(key)))

        if create_record and book_id:
            record = Export(
                book_id=book_id,
                user_id=document.user_id or (book.user_id if book else uuid.uuid4()),
                format=fmt,
                template=template,
                status="ready" if report.get("ok") else "failed",
                storage_key=key,
                size_bytes=len(data),
                page_count=page_count,
                checksum=digest,
                validation=report,
                renderer=renderer,
            )
            self.db.add(record)
            await self.db.flush()

        log.info(
            "export_rendered",
            book_id=str(book_id),
            format=fmt,
            bytes=len(data),
            renderer=renderer,
            ok=report.get("ok"),
        )
        return PublishedArtifact(
            format=fmt,
            storage_key=key,
            size_bytes=len(data),
            page_count=page_count,
            checksum=digest,
            renderer=renderer,
        )

    # -- public API used by the exports router ---------------------------
    async def create_and_store(
        self,
        book: Book,
        chapters: list[Any],
        *,
        fmt: str,
        template: str = "classic",
        page_size: str = "a5",
        include_front_matter: bool = True,
        include_toc: bool = True,
        author_bio: str | None = None,
    ) -> Export:
        document = await build_document(
            self.db,
            book,
            chapters,
            template=template,
            page_size=page_size,
            include_front_matter=include_front_matter,
            include_toc=include_toc,
            author_bio=author_bio,
        )
        artifact = await self.render_and_store(document, fmt, template=template, book=book)

        result = await self.db.execute(
            select(Export)
            .where(Export.book_id == book.id, Export.storage_key == artifact.storage_key)
            .order_by(Export.created_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = Export(
                book_id=book.id,
                user_id=book.user_id,
                format=fmt,
                template=template,
                status="ready",
                storage_key=artifact.storage_key,
                size_bytes=artifact.size_bytes,
                page_count=artifact.page_count,
                checksum=artifact.checksum,
                validation={},
                renderer=artifact.renderer,
            )
            self.db.add(record)
            await self.db.flush()
        return record

    async def download_url(self, export: Export, *, filename: str | None = None) -> str:
        from app.core.config import get_settings

        settings = get_settings()
        name = filename or f"{export.format}-export.{export.format}"
        if not export.storage_key:
            raise AppError(
                "This export has no stored file.",
                code="export_missing_file",
                status_code=409,
            )
        return get_storage().signed_url(
            export.storage_key, expires_in=settings.signed_url_expire_seconds, filename=name
        )
