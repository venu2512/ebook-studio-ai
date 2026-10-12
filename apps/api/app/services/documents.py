"""Book document assembly and rendering (PDF, EPUB, DOCX).

One normalised :class:`BookDocument` is built from the approved chapters, then
rendered to a shared HTML source and finally to each format so the outputs
match. HTML -> PDF uses WeasyPrint when installed, otherwise a built-in fpdf2
renderer (clearly marked as a lower-fidelity fallback).

Everything here is pure: no database access. The orchestrator passes in data.
"""

from __future__ import annotations

import html as html_lib
import io
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from markdown_it import MarkdownIt

from app.core.logging import get_logger

log = get_logger(__name__)

_md = (
    MarkdownIt("commonmark", {"html": False, "linkify": False})
    .enable("table")
    .enable("strikethrough")
)

DISCLAIMER_TEXT = (
    "This book is provided for general information and educational purposes only. "
    "It is not professional advice. Do not rely on it as a substitute for advice from "
    "a qualified professional. The author and publisher disclaim any liability arising "
    "from the use or misuse of the information in this book. Always consult a suitably "
    "qualified professional before acting on anything you read here. This title was "
    "produced with the assistance of AI and has been reviewed by the author."
)


@dataclass
class ChapterDoc:
    title: str
    markdown: str
    part_title: str | None = None
    order: int = 0
    is_front_matter: bool = False

    @property
    def word_count(self) -> int:
        return len(re.findall(r"\S+", self.markdown or ""))


@dataclass
class BookDocument:
    title: str
    subtitle: str | None = None
    author: str | None = None
    topic: str = ""
    description: str | None = None
    language: str = "en"
    book_id: Any | None = None
    user_id: Any | None = None
    copyright_year: int = field(default_factory=lambda: datetime.now(UTC).year)
    publisher: str = "eBook Studio AI"
    is_sensitive: bool = False
    include_front_matter: bool = True
    include_toc: bool = True
    include_disclaimer: bool = False
    template: str = "classic"
    page_size: str = "a5"
    palette: dict[str, str] = field(
        default_factory=lambda: {
            "primary": "#1F2937",
            "accent": "#F59E0B",
            "background": "#FFFFFF",
            "text": "#111827",
        }
    )
    chapters: list[ChapterDoc] = field(default_factory=list)
    author_bio: str | None = None
    cta_text: str | None = None
    cover_image_bytes: bytes | None = None
    cover_mime: str = "image/png"
    keywords: list[str] = field(default_factory=list)

    # -- derived -----------------------------------------------------------
    @property
    def total_word_count(self) -> int:
        return sum(c.word_count for c in self.chapters)

    @property
    def front_matter(self) -> list[str]:
        return ["title_page", "copyright"] + (["disclaimer"] if self.include_disclaimer else [])

    @property
    def disclaimer(self) -> str | None:
        return DISCLAIMER_TEXT if self.include_disclaimer else None

    def chapter_html(self) -> list[tuple[str, str]]:
        """Return ``[(title, html)]`` for each chapter, in order."""
        rendered: list[tuple[str, str]] = []
        for chapter in self.chapters:
            body = markdown_to_html(chapter.markdown)
            # Drop a leading H1/H2 that duplicates the chapter title.
            body = _strip_leading_heading(body)
            rendered.append((chapter.title, body))
        return rendered

    @property
    def html(self) -> str:
        return render_html(self)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def assemble_document(
    *,
    book: Any,
    chapters: list[Any],
    template: str = "classic",
    page_size: str = "a5",
    include_front_matter: bool = True,
    include_toc: bool = True,
    author_bio: str | None = None,
    palette: dict[str, str] | None = None,
    cover_image_bytes: bytes | None = None,
    extra_back_matter: list[str] | None = None,
) -> BookDocument:
    """Build a :class:`BookDocument` from ORM ``Book`` + ``Chapter`` objects."""
    sensitive = bool(getattr(book, "is_sensitive", False))
    doc = BookDocument(
        title=book.title,
        subtitle=book.subtitle,
        author=book.author_name or "Anonymous",
        topic=book.topic,
        description=book.description,
        language=book.language,
        book_id=getattr(book, "id", None),
        user_id=getattr(book, "user_id", None),
        is_sensitive=sensitive,
        include_front_matter=include_front_matter,
        include_toc=include_toc,
        include_disclaimer=sensitive,
        template=template,
        page_size=page_size,
        author_bio=author_bio,
        keywords=list(getattr(book, "keywords", []) or []),
        cover_image_bytes=cover_image_bytes,
        cta_text=(
            "If this book helped you, please leave an honest review. "
            "It helps other readers find it."
        ),
    )
    if palette:
        doc.palette = {**doc.palette, **palette}

    for chapter in sorted(chapters, key=lambda c: c.order_index):
        doc.chapters.append(
            ChapterDoc(
                title=chapter.title,
                markdown=chapter.content or "",
                part_title=chapter.part_title,
                order=chapter.order_index,
            )
        )
    return doc


# ---------------------------------------------------------------------------
# Markdown / HTML
# ---------------------------------------------------------------------------
def markdown_to_html(markdown: str) -> str:
    return _md.render(markdown or "")


def _strip_leading_heading(body: str) -> str:
    """Remove a leading <h1>/<h2> so the chapter heading isn't duplicated."""
    return re.sub(r"^\s*<h[12][^>]*>.*?</h[12]>\s*", "", body, count=1, flags=re.DOTALL)


def _esc(value: str | None) -> str:
    return html_lib.escape(value or "")


def render_html(doc: BookDocument) -> str:
    """Render the full book to a single self-contained HTML document."""
    palette = doc.palette
    parts: list[str] = []
    parts.append(
        f"""<!DOCTYPE html>
<html lang="{_esc(doc.language)}">
<head>
<meta charset="utf-8">
<title>{_esc(doc.title)}</title>
<style>
  :root {{
    --primary: {palette.get("primary", "#1F2937")};
    --accent: {palette.get("accent", "#F59E0B")};
    --bg: {palette.get("background", "#FFFFFF")};
    --text: {palette.get("text", "#111827")};
  }}
  body {{ font-family: Georgia, 'Times New Roman', serif; color: var(--text);
          background: var(--bg); line-height: 1.55; margin: 0; }}
  .page {{ max-width: 42em; margin: 0 auto; padding: 2.5em 2em; }}
  h1, h2, h3, h4 {{ font-family: 'Helvetica Neue', Arial, sans-serif;
                     color: var(--primary); line-height: 1.2; }}
  h1 {{ font-size: 2.2em; margin-top: 0; }}
  h2 {{ font-size: 1.7em; margin-top: 2em; page-break-before: always; }}
  h3 {{ font-size: 1.25em; margin-top: 1.6em; }}
  .accent {{ color: var(--accent); }}
  .title-page {{ text-align: center; padding: 22% 1em; }}
  .title-page .title {{ font-size: 2.6em; font-weight: 700; }}
  .title-page .subtitle {{ font-size: 1.2em; margin-top: .6em; color: #4b5563; }}
  .title-page .author {{ margin-top: 3em; font-size: 1.1em; }}
  .copyright, .disclaimer {{ font-size: .85em; color: #4b5563; }}
  .disclaimer {{ border-left: 4px solid var(--accent); padding-left: 1em; margin: 2em 0; }}
  .toc ol {{ list-style: none; padding-left: 0; }}
  .toc li {{ margin: .35em 0; }}
  .toc .part {{ margin-top: 1em; font-weight: 700; }}
  .chapter {{ margin-top: 2em; }}
  blockquote {{ border-left: 4px solid var(--accent); margin: 1.2em 0;
                padding: .2em 1em; color: #374151; background: #fafafa; }}
  pre, code {{ font-family: 'SFMono-Regular', Consolas, monospace; background: #f3f4f6; }}
  pre {{ padding: 1em; overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1.2em 0; }}
  th, td {{ border: 1px solid #d1d5db; padding: .5em .7em; text-align: left; }}
  .checklist li {{ list-style: none; }}
  img {{ max-width: 100%; }}
  .cover {{ text-align: center; }}
  .cover img {{ max-height: 90vh; }}
</style>
</head>
<body>
<div class="page">
"""
    )

    # Cover
    if doc.cover_image_bytes:
        import base64

        b64 = base64.b64encode(doc.cover_image_bytes).decode("ascii")
        parts.append(
            f'<div class="cover"><img src="data:{doc.cover_mime};base64,{b64}" '
            f'alt="{_esc(doc.title)} cover"></div>'
        )

    # Front matter
    if doc.include_front_matter:
        parts.append(
            f"""<section class="title-page">
  <div class="title">{_esc(doc.title)}</div>
  {f'<div class="subtitle">{_esc(doc.subtitle)}</div>' if doc.subtitle else ""}
  <div class="author">by {_esc(doc.author)}</div>
</section>
<section class="copyright">
  <p>&copy; {doc.copyright_year} {_esc(doc.author)}. All rights reserved.</p>
  <p>Published by {_esc(doc.publisher)}. No part of this book may be reproduced
     without written permission, except brief quotations in a review.</p>
  <p>Produced with AI assistance and reviewed by the author.</p>
</section>"""
        )
        if doc.include_disclaimer:
            parts.append(
                f'<section class="disclaimer"><h2>Important Disclaimer</h2>'
                f"<p>{_esc(DISCLAIMER_TEXT)}</p></section>"
            )

    # Table of contents
    if doc.include_toc and doc.chapters:
        parts.append(_render_toc(doc))

    # Chapters
    for index, (title, body) in enumerate(doc.chapter_html(), start=1):
        anchor = f"chapter-{index}"
        parts.append(
            f'<section class="chapter" id="{anchor}">\n'
            f"<h2>{index}. {_esc(title)}</h2>\n{body}\n</section>"
        )

    # Back matter
    parts.append('<section class="back-matter">')
    if doc.author_bio:
        parts.append(f"<h2>About the Author</h2><p>{_esc(doc.author_bio)}</p>")
    if doc.cta_text:
        parts.append(f"<h2>One Last Thing</h2><p>{_esc(doc.cta_text)}</p>")
    parts.append("</section>")

    parts.append("</div>\n</body>\n</html>")
    return "".join(parts)


def _render_toc(doc: BookDocument) -> str:
    items: list[str] = []
    current_part: str | None = None
    for index, chapter in enumerate(doc.chapters, start=1):
        if chapter.part_title and chapter.part_title != current_part:
            current_part = chapter.part_title
            items.append(f'<li class="part">{_esc(current_part)}</li>')
        items.append(f'<li><a href="#chapter-{index}">{index}. {_esc(chapter.title)}</a></li>')
    return f'<nav class="toc"><h2>Contents</h2><ol>{"".join(items)}</ol></nav>'


def plain_text(doc: BookDocument) -> str:
    """A plain-text rendition used for word counts and the DOCX fallback."""
    blocks = [doc.title]
    if doc.subtitle:
        blocks.append(doc.subtitle)
    for chapter in doc.chapters:
        blocks.append(chapter.title)
        blocks.append(_md_to_text(chapter.markdown))
    return "\n\n".join(blocks)


def _md_to_text(markdown: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", markdown or "", flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------
def render_pdf(doc: BookDocument) -> tuple[bytes, str]:
    """Render to PDF. Returns ``(bytes, renderer_name)``."""
    weasy = _try_render_pdf_weasyprint(doc)
    if weasy is not None:
        return weasy, "weasyprint"
    return _render_pdf_fpdf(doc), "fpdf2"


def _try_render_pdf_weasyprint(doc: BookDocument) -> bytes | None:
    try:
        from weasyprint import HTML

        return HTML(string=doc.html).write_pdf()
    except Exception as exc:  # noqa: BLE001 - optional dependency / system libs
        log.warning("weasyprint_unavailable", error=str(exc))
        return None


def _render_pdf_fpdf(doc: BookDocument) -> bytes:
    """Dependency-light PDF fallback (Latin-1 text only). TODO: fidelity."""
    import warnings

    from fpdf import FPDF

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # A5 dimensions warning
        pdf = FPDF(format=_fpdf_format(doc.page_size))
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)

    # Title page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 26)
    pdf.ln(70)
    _fpdf_mc(pdf, 12, doc.title, align="C")
    if doc.subtitle:
        pdf.set_font("Helvetica", "", 14)
        pdf.ln(4)
        _fpdf_mc(pdf, 8, doc.subtitle, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(20)
    _fpdf_mc(pdf, 8, f"by {doc.author}", align="C")

    # Copyright + disclaimer
    pdf.add_page()
    pdf.set_font("Helvetica", "", 9)
    _fpdf_mc(pdf, 5, f"(c) {doc.copyright_year} {doc.author}. All rights reserved.")
    if doc.include_disclaimer:
        pdf.ln(6)
        _fpdf_mc(pdf, 5, "IMPORTANT DISCLAIMER: " + DISCLAIMER_TEXT)

    # Contents
    if doc.include_toc:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        _fpdf_mc(pdf, 10, "Contents")
        pdf.set_font("Helvetica", "", 11)
        for index, chapter in enumerate(doc.chapters, start=1):
            _fpdf_mc(pdf, 7, f"{index}. {chapter.title}")

    # Chapters
    for index, chapter in enumerate(doc.chapters, start=1):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        _fpdf_mc(pdf, 10, f"{index}. {chapter.title}")
        pdf.ln(2)
        _fpdf_write_markdown(pdf, chapter.markdown)

    return bytes(pdf.output())


def _fpdf_mc(pdf: Any, height: float, text: str, *, align: str = "L") -> None:
    """multi_cell that always returns to the left margin on the next line."""
    pdf.multi_cell(0, height, _ascii(text), align=align, new_x="LMARGIN", new_y="NEXT")


def _fpdf_format(page_size: str) -> str:
    return {"a5": "A5", "a4": "A4", "letter": "Letter"}.get(page_size, "A5")


def _fpdf_write_markdown(pdf: Any, markdown: str) -> None:
    for raw_line in (markdown or "").splitlines():
        line = raw_line.rstrip()
        if not line:
            pdf.ln(3)
            continue
        if line.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(2)
            _fpdf_mc(pdf, 7, line[4:])
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.ln(2)
            _fpdf_mc(pdf, 8, line[3:])
        elif line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            _fpdf_mc(pdf, 9, line[2:])
        elif re.match(r"^[-*]\s+", line):
            pdf.set_font("Helvetica", "", 11)
            _fpdf_mc(pdf, 6, "  \u2022 " + re.sub(r"^[-*]\s+", "", line))
        else:
            pdf.set_font("Helvetica", "", 11)
            _fpdf_mc(pdf, 6, _md_to_text(line))
    pdf.ln(2)


def _ascii(text: str) -> str:
    return text.encode("latin-1", "replace").decode("latin-1")


def render_epub(doc: BookDocument) -> bytes:
    """Render an EPUB 3 file with a nav document and NCX fallback."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier(f"ebookstudio-{abs(hash(doc.title))}")
    book.set_title(doc.title)
    book.set_language(doc.language)
    book.add_author(doc.author or "Anonymous")

    if doc.description:
        book.add_metadata("DC", "description", doc.description)
    for keyword in doc.keywords[:10]:
        book.add_metadata("DC", "subject", keyword)

    if doc.cover_image_bytes:
        book.set_cover("cover.png", doc.cover_image_bytes)

    style = epub.EpubItem(
        uid="style",
        file_name="style/book.css",
        media_type="text/css",
        content=_EPUB_CSS.encode("utf-8"),
    )
    book.add_item(style)

    spine: list[Any] = ["nav"]
    toc: list[Any] = []

    # Title page
    if doc.include_front_matter:
        title_page = epub.EpubHtml(title="Title Page", file_name="title.xhtml", lang=doc.language)
        title_page.content = (
            f"<h1>{_esc(doc.title)}</h1>"
            + (f"<h2>{_esc(doc.subtitle)}</h2>" if doc.subtitle else "")
            + f"<p>by {_esc(doc.author)}</p>"
        )
        title_page.add_item(style)
        book.add_item(title_page)
        spine.append(title_page)
        toc.append(title_page)

        copyright_page = epub.EpubHtml(
            title="Copyright", file_name="copyright.xhtml", lang=doc.language
        )
        copyright_page.content = (
            f"<p>&copy; {doc.copyright_year} {_esc(doc.author)}. All rights reserved.</p>"
            + (
                f"<h2>Disclaimer</h2><p>{_esc(DISCLAIMER_TEXT)}</p>"
                if doc.include_disclaimer
                else ""
            )
        )
        copyright_page.add_item(style)
        book.add_item(copyright_page)
        spine.append(copyright_page)
        toc.append(copyright_page)

    # Chapters
    epub_chapters: list[Any] = []
    for index, (title, body) in enumerate(doc.chapter_html(), start=1):
        item = epub.EpubHtml(title=title, file_name=f"chapter_{index:02d}.xhtml", lang=doc.language)
        item.content = f"<h2>{index}. {_esc(title)}</h2>{body}"
        item.add_item(style)
        book.add_item(item)
        spine.append(item)
        epub_chapters.append(item)
    if epub_chapters:
        toc.append((epub.Section("Chapters"), epub_chapters))

    if doc.author_bio:
        about = epub.EpubHtml(title="About the Author", file_name="about.xhtml", lang=doc.language)
        about.content = f"<h2>About the Author</h2><p>{_esc(doc.author_bio)}</p>"
        about.add_item(style)
        book.add_item(about)
        spine.append(about)
        toc.append(about)

    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    buffer = io.BytesIO()
    epub.write_epub(buffer, book)
    return buffer.getvalue()


def render_docx(doc: BookDocument) -> bytes:
    """Render a DOCX that mirrors the PDF/EPUB structure."""
    from docx import Document
    from docx.shared import Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Georgia"
    style.font.size = Pt(11)

    # Title page
    document.add_heading(doc.title, level=0)
    if doc.subtitle:
        document.add_paragraph(doc.subtitle)
    document.add_paragraph(f"by {doc.author}")
    document.add_page_break()

    # Copyright + disclaimer
    document.add_paragraph(f"© {doc.copyright_year} {doc.author}. All rights reserved.")
    if doc.include_disclaimer:
        document.add_heading("Important Disclaimer", level=2)
        document.add_paragraph(DISCLAIMER_TEXT)
    document.add_page_break()

    # Table of contents
    if doc.include_toc:
        document.add_heading("Contents", level=1)
        for index, chapter in enumerate(doc.chapters, start=1):
            document.add_paragraph(f"{index}. {chapter.title}", style="List Number")
        document.add_page_break()

    # Chapters
    for index, chapter in enumerate(doc.chapters, start=1):
        if index > 1:
            document.add_page_break()
        document.add_heading(f"{index}. {chapter.title}", level=1)
        _docx_write_markdown(document, chapter.markdown)

    if doc.author_bio:
        document.add_page_break()
        document.add_heading("About the Author", level=1)
        document.add_paragraph(doc.author_bio)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _docx_write_markdown(document: Any, markdown: str) -> None:
    for raw_line in (markdown or "").splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("### "):
            document.add_heading(_md_to_text(line[4:]), level=3)
        elif line.startswith("## "):
            document.add_heading(_md_to_text(line[3:]), level=2)
        elif line.startswith("# "):
            document.add_heading(_md_to_text(line[2:]), level=2)
        elif line.startswith("> "):
            document.add_paragraph(_md_to_text(line[2:]), style="Intense Quote")
        elif re.match(r"^\s*[-*]\s+", line):
            document.add_paragraph(
                _md_to_text(re.sub(r"^\s*[-*]\s+", "", line)), style="List Bullet"
            )
        elif re.match(r"^\s*\d+\.\s+", line):
            document.add_paragraph(
                _md_to_text(re.sub(r"^\s*\d+\.\s+", "", line)), style="List Number"
            )
        else:
            document.add_paragraph(_md_to_text(line))


_EPUB_CSS = """\
body { font-family: Georgia, serif; line-height: 1.5; }
h1, h2, h3 { font-family: Helvetica, Arial, sans-serif; }
blockquote { border-left: 3px solid #F59E0B; padding-left: 1em; color: #374151; }
table { border-collapse: collapse; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.6em; }
"""


RENDERERS = {
    "pdf": render_pdf,
    "epub": render_epub,
    "docx": render_docx,
}


def render(doc: BookDocument, fmt: str) -> tuple[bytes, str]:
    """Render ``doc`` to ``fmt``. Returns ``(bytes, renderer_name)``."""
    if fmt == "pdf":
        return render_pdf(doc)
    if fmt == "epub":
        return render_epub(doc), "ebooklib"
    if fmt == "docx":
        return render_docx(doc), "python-docx"
    raise ValueError(f"Unsupported format: {fmt}")
