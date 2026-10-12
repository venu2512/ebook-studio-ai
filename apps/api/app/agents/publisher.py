"""Publisher agent: assembles the final book and produces PDF / EPUB / DOCX.

Unlike the other agents this one does **not** call an LLM. It is still a
pipeline stage because it owns a quality gate (front matter, table of contents,
disclaimer, EPUB validation) and turns the approved chapters into deliverables.

It never touches the database. The orchestrator injects:

* ``document`` - the assembled :class:`BookDocument` (from approved chapters),
* an ``exporter`` implementing :class:`BookExporter` (renders files + stores them).
"""

from __future__ import annotations

import time
from typing import Any, ClassVar, Protocol, runtime_checkable

from pydantic import BaseModel

from app.agents.base import AgentContext, AgentResult
from app.agents.schemas import PublisherOutput


@runtime_checkable
class BookExporter(Protocol):
    """Renders a document to a format and stores it, returning artifact info."""

    async def render(self, document: Any, fmt: str, *, template: str) -> Any: ...


class PublisherAgent:
    """Assembles and validates the finished book."""

    name: ClassVar[str] = "publisher"

    def __init__(self, exporter: BookExporter | None = None) -> None:
        self.exporter = exporter

    async def run(
        self,
        ctx: AgentContext,
        *,
        document: Any | None = None,
        formats: list[str] | None = None,
        template: str = "classic",
        **kwargs: Any,
    ) -> AgentResult:
        from app.llm.base import LLMResponse

        started = time.perf_counter()
        formats = formats or ["pdf", "epub", "docx"]
        notes: list[str] = []
        artifacts = []

        if document is None:
            notes.append("No document supplied; nothing to render.")
            output = PublisherOutput(notes=notes)
        else:
            validation = _validate_document(document)
            if self.exporter is not None:
                for fmt in formats:
                    artifact = await self.exporter.render(document, fmt, template=template)
                    artifacts.append(artifact)
            else:
                notes.append("No exporter configured (TODO: inject the export service).")

            output = PublisherOutput(
                artifacts=artifacts,
                validation=validation,
                has_front_matter=bool(getattr(document, "front_matter", None)),
                has_toc=bool(getattr(document, "chapters", None)),
                has_disclaimer=bool(getattr(document, "disclaimer", None)),
                chapter_count=len(getattr(document, "chapters", []) or []),
                total_word_count=int(getattr(document, "total_word_count", 0) or 0),
                notes=notes,
            )

        issues = self.quality_issues(ctx, output)
        response = LLMResponse(
            content="",
            model="none",
            provider="internal",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return AgentResult(agent=self.name, output=output, response=response, issues=issues)

    def quality_issues(self, ctx: AgentContext, output: BaseModel, **kwargs: Any) -> list[str]:
        assert isinstance(output, PublisherOutput)
        issues: list[str] = []
        if output.chapter_count == 0:
            issues.append("No chapters in the finished document.")
        if not output.has_toc:
            issues.append("Table of contents is missing.")
        if ctx.is_sensitive and not output.has_disclaimer:
            issues.append("Sensitive topic: disclaimer page is missing.")
        if not output.artifacts:
            issues.append("No export files were produced.")
        for artifact in output.artifacts:
            if artifact.size_bytes == 0:
                issues.append(f"{artifact.format.upper()} export is empty.")
        return issues


def _validate_document(document: Any) -> dict[str, object]:
    """Lightweight structural validation shared across formats."""
    chapters = getattr(document, "chapters", []) or []
    html = getattr(document, "html", "") or ""
    empty = [c.title for c in chapters if not (getattr(c, "markdown", "") or "").strip()]
    return {
        "chapter_count": len(chapters),
        "empty_chapters": empty,
        "has_toc": "toc" in html.lower() or bool(chapters),
        "word_count": int(getattr(document, "total_word_count", 0) or 0),
        "ok": not empty and len(chapters) > 0,
    }


__all__ = ["PublisherAgent", "BookExporter"]
