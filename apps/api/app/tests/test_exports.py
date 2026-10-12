"""Document rendering and export validation (PDF / EPUB / DOCX)."""

from __future__ import annotations

import io
import uuid
import zipfile
from types import SimpleNamespace

from app.services import documents as docs
from app.services import exports as exports_service


def _book(*, sensitive: bool = False):
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="The Bread Book",
        subtitle="A beginner's guide",
        author_name="A Baker",
        topic="Bread baking",
        description=None,
        language="en",
        is_sensitive=sensitive,
        keywords=["bread", "baking"],
    )


def _chapters():
    return [
        SimpleNamespace(
            order_index=0,
            title="Getting Started",
            content="## Getting Started\n\nMix the dough and let it rest.\n\n- Flour\n- Water",
            part_title="Part I",
        ),
        SimpleNamespace(
            order_index=1,
            title="Baking",
            content="## Baking\n\nHeat the oven and bake until golden.",
            part_title="Part I",
        ),
    ]


def test_assemble_document_includes_sensitive_disclaimer():
    doc = docs.assemble_document(book=_book(sensitive=True), chapters=_chapters())
    assert doc.is_sensitive is True
    assert doc.include_disclaimer is True
    assert doc.disclaimer
    assert len(doc.chapters) == 2
    assert doc.total_word_count > 0


def test_render_pdf_is_valid():
    doc = docs.assemble_document(book=_book(), chapters=_chapters())
    data, renderer = docs.render(doc, "pdf")
    assert data[:5] == b"%PDF-"
    report = exports_service.validate_export(data, "pdf", doc)
    assert report["ok"] is True
    assert report["checks"]["header"] and report["checks"]["eof"]
    assert report["chapter_count"] == 2
    assert renderer


def test_render_epub_is_valid_zip():
    doc = docs.assemble_document(book=_book(), chapters=_chapters())
    data, _ = docs.render(doc, "epub")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
    assert "mimetype" in names
    assert "META-INF/container.xml" in names
    report = exports_service.validate_export(data, "epub", doc)
    assert report["ok"] is True


def test_render_docx_is_valid_zip():
    doc = docs.assemble_document(book=_book(), chapters=_chapters())
    data, _ = docs.render(doc, "docx")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
    assert "word/document.xml" in names
    assert "[Content_Types].xml" in names
    report = exports_service.validate_export(data, "docx", doc)
    assert report["ok"] is True


def test_estimate_pages_is_monotonic():
    small = docs.BookDocument(title="t", chapters=[docs.ChapterDoc(title="c", markdown="a b c")])
    large = docs.BookDocument(
        title="t",
        chapters=[docs.ChapterDoc(title="c", markdown="word " * 5000)],
    )
    assert exports_service.estimate_pages(large) > exports_service.estimate_pages(small)


def test_storage_key_is_deterministic():
    book_id = uuid.uuid4()
    key = exports_service.storage_key(book_id, "pdf", "classic")
    assert key == f"exports/{book_id}/classic-pdf-v0.pdf"
