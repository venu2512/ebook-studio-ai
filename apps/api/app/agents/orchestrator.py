"""The orchestrator: a resumable state machine that runs the agent pipeline.

It is the only component that persists agent results. Agents stay pure; services
own the database. Each step is recorded as an :class:`AgentRun` with a stable
``step_key`` so a job can resume after a worker restart and so retries never
double-charge or duplicate work.

Pipeline
--------
``outline`` job:  research -> plan
``full_book`` job: (writer -> editor -> fact_checker) per chapter -> design ->
                   publish -> marketing
``chapter`` job:  writer -> editor -> fact_checker for one chapter
``cover`` job:    design + cover image
``export`` job:   publish
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import (
    AgentContext,
    AgentResult,
    DesignerAgent,
    EditorAgent,
    FactCheckerAgent,
    MarketerAgent,
    PublisherAgent,
    WriterAgent,
)
from app.agents.base import hash_input
from app.agents.schemas import ChapterDraft, ResearchOutput
from app.core.config import get_settings
from app.core.errors import AppError, BudgetExceededError
from app.core.logging import get_logger
from app.db.models import AgentRun, Book, Chapter, Job
from app.services import books as books_service
from app.services import chapters as chapters_service
from app.services import covers as covers_service
from app.services import exports as exports_service
from app.services import marketing as marketing_service
from app.services import outline as outline_service

log = get_logger(__name__)

# Rough token split when allocating the budget across chapters.
PUBLISH_FORMATS = ["pdf", "epub", "docx"]


class JobCancelled(Exception):
    """Raised internally when the user cancels a job."""


class Orchestrator:
    def __init__(self, db: AsyncSession, job: Job, book: Book) -> None:
        self.db = db
        self.job = job
        self.book = book
        self.settings = get_settings()
        self.tokens_this_run = 0
        self.cost_this_run = 0.0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    async def run(self) -> Job:
        self.job.status = "running"
        self.job.started_at = self.job.started_at or datetime.now(UTC)
        self.job.error = None
        self.job.error_code = None
        await self.db.flush()

        try:
            if self.job.type == "outline":
                await self._run_outline()
            elif self.job.type == "chapter":
                await self._run_chapter()
            elif self.job.type == "cover":
                await self._run_cover()
            elif self.job.type == "export":
                await self._run_export()
            else:
                await self._run_full_book()

            self.job.status = "succeeded"
            self.job.progress_pct = 100
            self.job.current_step = None
            self.job.finished_at = datetime.now(UTC)
            log.info("job_succeeded", job_id=str(self.job.id), type=self.job.type)
        except JobCancelled:
            self.job.status = "cancelled"
            self.job.error = "Generation was cancelled."
            self.job.finished_at = datetime.now(UTC)
            log.info("job_cancelled", job_id=str(self.job.id))
        except BudgetExceededError as exc:
            self.job.status = "failed"
            self.job.error_code = exc.code
            self.job.error = exc.message + " Your completed chapters are saved and downloadable."
            self.job.finished_at = datetime.now(UTC)
            log.warning("job_budget_exceeded", job_id=str(self.job.id))
        except Exception as exc:
            self.job.status = "failed"
            self.job.error_code = getattr(exc, "code", "job_failed")
            self.job.error = getattr(exc, "message", None) or str(exc)
            self.job.finished_at = datetime.now(UTC)
            log.exception("job_failed", job_id=str(self.job.id), error=str(exc))

        await self.db.flush()
        return self.job

    # ------------------------------------------------------------------
    # Step bookkeeping
    # ------------------------------------------------------------------
    def reverify(self) -> None:
        if self.job.cancel_requested:
            raise JobCancelled()

    def _is_done(self, step_key: str) -> bool:
        return step_key in (self.job.completed_steps or [])

    def _mark_done(self, step_key: str) -> None:
        steps = list(self.job.completed_steps or [])
        if step_key not in steps:
            steps.append(step_key)
        self.job.completed_steps = steps

    async def _step(self, step_key: str, progress: int, label: str | None = None) -> None:
        self.reverify()
        self.job.current_step = label or step_key
        self.job.progress_pct = progress
        await self.db.flush()

    def _context(self) -> AgentContext:
        ctx = books_service.build_agent_context(self.book)
        ctx.job_id = self.job.id
        ctx.style_guide = chapters_service.build_style_guide(self.book)
        return ctx

    async def _record(
        self,
        result: AgentResult | None,
        *,
        agent: str,
        step_key: str,
        input_payload: dict[str, Any],
        status: str = "succeeded",
        error: str | None = None,
        attempt: int = 1,
    ) -> AgentRun:
        """Persist an AgentRun and fold its usage into the book totals."""
        chapter_id = input_payload.get("chapter_id")
        if isinstance(chapter_id, str):
            try:
                chapter_id = uuid.UUID(chapter_id)
            except ValueError:
                chapter_id = None
        run = AgentRun(
            job_id=self.job.id,
            book_id=self.book.id,
            chapter_id=chapter_id,
            agent_name=agent,
            input_hash=hash_input(input_payload),
            step_key=step_key,
            status=status,
            attempt=attempt,
            error=error,
        )
        if result is not None:
            run.model = result.response.model
            run.prompt_tokens = result.response.prompt_tokens
            run.completion_tokens = result.response.completion_tokens
            run.total_tokens = result.response.total_tokens
            run.cost_usd = result.response.cost_usd
            run.duration_ms = result.response.latency_ms
            run.raw_output = result.response.content[:20000]
            try:
                run.output = result.output.model_dump(mode="json")
            except Exception:  # noqa: BLE001 - keep going, output is best-effort
                run.output = {}
            self.tokens_this_run += result.response.total_tokens
            self.cost_this_run += result.response.cost_usd
            self.book.tokens_used = (self.book.tokens_used or 0) + result.response.total_tokens
            self.book.cost_usd = round((self.book.cost_usd or 0.0) + result.response.cost_usd, 6)
        self.db.add(run)
        await self.db.flush()
        return run

    def _check_budget(self) -> None:
        if (self.book.tokens_used or 0) >= (self.book.token_budget or 0):
            # Auto-expand budget up to 10M tokens so full generation never fails
            if (self.book.token_budget or 0) < 10_000_000:
                self.book.token_budget = max((self.book.tokens_used or 0) + 1_000_000, 2_500_000)
                log.info(
                    "book_token_budget_auto_expanded",
                    book_id=str(self.book.id),
                    new_budget=self.book.token_budget,
                )
                return
            raise BudgetExceededError(
                f"Token budget of {self.book.token_budget:,} was reached.",
                details={"tokens_used": self.book.tokens_used, "budget": self.book.token_budget},
            )

    # ------------------------------------------------------------------
    # Outline job
    # ------------------------------------------------------------------
    async def _run_outline(self) -> None:
        ctx = self._context()
        await self._step("research", 10, "research")
        if not self._is_done("research"):
            research_result = await outline_service.run_research(ctx)
            research_output = cast(ResearchOutput, research_result.output)
            if research_output.notes:
                await outline_service.save_research_notes(self.db, self.book, research_output.notes)
            ctx.research_notes = research_output.notes
            await self._record(
                research_result,
                agent="researcher",
                step_key="research",
                input_payload={"book_id": str(self.book.id)},
            )
            self._mark_done("research")
        else:
            ctx.research_notes = await outline_service.load_research_notes(self.db, self.book.id)

        await self._step("plan", 60, "plan")
        if not self._is_done("plan"):
            outline, _, planner_result = await outline_service.generate_outline(
                self.db, self.book, ctx, reuse_research=True, persist_research=False
            )
            await self._record(
                planner_result,
                agent="planner",
                step_key="plan",
                input_payload={"book_id": str(self.book.id), "v": outline.version},
            )
            self._mark_done("plan")

        self.book.status = "awaiting_approval"
        await self.db.flush()

    # ------------------------------------------------------------------
    # Full book job
    # ------------------------------------------------------------------
    async def _run_full_book(self) -> None:
        outline = await outline_service.get_latest_outline(self.db, self.book.id)
        if outline is None or not outline.is_approved:
            raise AppError(
                "Approve the outline before generating the full book.",
                code="outline_not_approved",
                status_code=409,
            )

        ctx = self._context()
        ctx.research_notes = await outline_service.load_research_notes(self.db, self.book.id)
        chapters = await chapters_service.list_chapters(self.db, self.book.id)
        if not chapters:
            raise AppError("This book has no chapters.", code="no_chapters")

        self.book.status = "writing"
        total = len(chapters)
        bible_summaries: list[str] = []

        for index, chapter in enumerate(chapters):
            self.reverify()
            self._check_budget()
            base = int(index / total * 70)
            span = max(1, int(70 / total))
            previous_summary = (
                bible_summaries[-1] if bible_summaries else "(this is the first chapter)"
            )

            _draft, summary = await self._write_chapter(ctx, chapter, previous_summary, base, span)
            if summary:
                bible_summaries.append(summary)

        # Design + cover
        await self._run_design(base_progress=78)
        # Publish exports
        await self._run_publish(base_progress=88)
        # Marketing
        await self._run_marketing(base_progress=95)

        self.book.status = "ready"
        # Persist the running bible for future regenerations.
        self.book.bible = {
            **(self.book.bible or {}),
            "chapter_summaries": bible_summaries,
        }
        await self.db.flush()

    async def _write_chapter(
        self,
        ctx: AgentContext,
        chapter: Chapter,
        previous_summary: str,
        base_progress: int,
        span: int,
    ) -> tuple[str | None, str]:
        """Run writer -> editor -> fact checker for one chapter."""
        order = chapter.order_index
        target_words = chapter.target_word_count or max(
            500,
            (self.book.target_word_count or 6000) // max(1, len(ctx.bible.chapter_summaries) + 3),
        )
        writer_key = f"writer:{order}"
        editor_key = f"editor:{order}"
        fact_key = f"fact:{order}"

        summary = chapter.summary or ""

        # -- Writer -----------------------------------------------------
        if not self._is_done(writer_key):
            chapter.status = "generating"
            await self._step(writer_key, base_progress, f"writer:{chapter.title[:40]}")
            await self.db.flush()
            try:
                result = await WriterAgent().run(
                    ctx,
                    chapter_number=order + 1,
                    chapter_title=chapter.title,
                    chapter_summary=chapter.summary or "",
                    key_points=chapter.key_points,
                    target_word_count=target_words,
                    previous_summary=previous_summary,
                )
            except Exception as exc:
                chapter.status = "failed"
                await self._record(
                    None,
                    agent="writer",
                    step_key=writer_key,
                    input_payload={"chapter_id": str(chapter.id)},
                    status="failed",
                    error=str(exc),
                )
                raise
            draft: ChapterDraft = result.output  # type: ignore[assignment]
            chapter.content = draft.markdown
            chapter.word_count = chapters_service.word_count(draft.markdown)
            chapter.summary = draft.summary or chapter.summary
            summary = draft.summary or summary
            if draft.key_points:
                chapter.key_points = draft.key_points
            await chapters_service.create_version(
                self.db, chapter, content=draft.markdown, source="agent"
            )
            if result.issues:
                chapter.flags = [
                    *chapter.flags,
                    *[{"type": "quality", "message": i} for i in result.issues],
                ]
            await self._record(
                result,
                agent="writer",
                step_key=writer_key,
                input_payload={"chapter_id": str(chapter.id), "order": order},
            )
            self._mark_done(writer_key)
            chapter.status = "drafted"
            await self.db.flush()
        else:
            summary = chapter.summary or summary

        # -- Editor -----------------------------------------------------
        if not self._is_done(editor_key):
            await self._step(
                editor_key, base_progress + max(1, span // 2), f"editor:{chapter.title[:40]}"
            )
            result = await EditorAgent().run(
                ctx, chapter_title=chapter.title, markdown=chapter.content or ""
            )
            edited = result.output.markdown  # type: ignore[attr-defined]
            if edited.strip():
                chapter.content = edited
                chapter.word_count = chapters_service.word_count(edited)
                await chapters_service.create_version(
                    self.db,
                    chapter,
                    content=edited,
                    source="agent",
                    editor_notes="; ".join(result.output.change_notes[:3]),  # type: ignore[attr-defined]
                )
            await self._record(
                result,
                agent="editor",
                step_key=editor_key,
                input_payload={"chapter_id": str(chapter.id), "order": order},
            )
            self._mark_done(editor_key)
            chapter.status = "edited"
            await self.db.flush()

        # -- Fact checker ----------------------------------------------
        if not self._is_done(fact_key):
            await self._step(fact_key, base_progress + span, f"fact_check:{chapter.title[:40]}")
            result = await FactCheckerAgent().run(
                ctx, chapter_title=chapter.title, markdown=chapter.content or ""
            )
            output = result.output
            assert hasattr(output, "claims")
            chapter.fact_checks = [c.model_dump(mode="json") for c in output.claims]
            # Apply the fact-checker's corrected markdown if it removed claims.
            corrected = getattr(output, "corrected_markdown", None)
            if (
                corrected
                and corrected.strip()
                and corrected != chapter.content
                and getattr(output, "unsupported_count", 0) > 0
            ):
                chapter.content = corrected
                chapter.word_count = chapters_service.word_count(corrected)
                await chapters_service.create_version(
                    self.db,
                    chapter,
                    content=corrected,
                    source="agent",
                    editor_notes="Fact checker corrections",
                )
            flags: list[dict[str, Any]] = []
            for claim in output.claims:
                if claim.verdict in ("unsupported", "needs_source"):
                    flags.append(
                        {
                            "type": "unverified_claim",
                            "message": claim.claim[:300],
                            "verdict": claim.verdict,
                            "correction": claim.correction,
                        }
                    )
            for note in getattr(output, "sensitive_flags", []) or []:
                flags.append({"type": "sensitive", "message": note})
            if flags:
                chapter.flags = [*chapter.flags, *flags]
            await self._record(
                result,
                agent="fact_checker",
                step_key=fact_key,
                input_payload={"chapter_id": str(chapter.id), "order": order},
            )
            self._mark_done(fact_key)
            chapter.status = "fact_checked"
            await self.db.flush()

        return chapter.content, summary

    # ------------------------------------------------------------------
    # Chapter-only job
    # ------------------------------------------------------------------
    async def _run_chapter(self) -> None:
        if not self.job.target_chapter_id:
            raise AppError("No chapter specified for this job.", code="missing_chapter")
        chapter = await chapters_service.get_chapter(
            self.db, self.book.id, self.job.target_chapter_id
        )
        ctx = self._context()
        ctx.research_notes = await outline_service.load_research_notes(self.db, self.book.id)
        self.book.status = "writing"
        await self._write_chapter(ctx, chapter, "(regeneration)", 20, 50)
        if chapter.status == "fact_checked":
            chapter.status = "edited"
        await self.db.flush()

    # ------------------------------------------------------------------
    # Design + cover
    # ------------------------------------------------------------------
    async def _run_design(self, base_progress: int) -> None:
        await self._step("design", base_progress, "design")
        if self._is_done("design"):
            return
        ctx = self._context()
        result = await DesignerAgent().run(ctx)
        design = result.output
        palette = getattr(design, "palette", {}) or {}
        await self._record(
            result,
            agent="designer",
            step_key="design",
            input_payload={"book_id": str(self.book.id)},
        )
        self.book.metadata_json = {
            **(self.book.metadata_json or {}),
            "design": design.model_dump(mode="json"),
            "template": getattr(design, "interior_template", "classic"),
        }
        self._mark_done("design")
        await self.db.flush()

        # Cover
        try:
            await covers_service.generate_cover(
                self.db,
                self.book,
                palette=palette,
                cover_prompt=getattr(design, "cover_prompt", None),
            )
        except Exception as exc:  # noqa: BLE001 - a cover failure must not fail the book
            log.warning("cover_generation_failed", book_id=str(self.book.id), error=str(exc))
        self.book.status = "designing"
        await self.db.flush()

    # ------------------------------------------------------------------
    # Publish (exports)
    # ------------------------------------------------------------------
    async def _run_publish(self, base_progress: int) -> None:
        await self._step("publish", base_progress, "publish")
        if self._is_done("publish"):
            return
        chapters = await chapters_service.list_chapters(self.db, self.book.id)
        export_service = exports_service.ExportService(self.db)
        reader = PublisherAgent(exporter=export_service)
        ctx = self._context()
        ctx.style_guide = chapters_service.build_style_guide(self.book)
        document = await exports_service.build_document(
            self.db,
            self.book,
            chapters,
            template=(self.book.metadata_json or {}).get("template", "classic"),
            page_size=(self.book.metadata_json or {}).get("page_size", "a5"),
            author_bio=(self.book.metadata_json or {}).get("author_bio"),
        )
        result = await reader.run(
            ctx,
            document=document,
            formats=PUBLISH_FORMATS,
            template=(self.book.metadata_json or {}).get("template", "classic"),
        )
        await self._record(
            result,
            agent="publisher",
            step_key="publish",
            input_payload={"book_id": str(self.book.id), "formats": PUBLISH_FORMATS},
        )
        self._mark_done("publish")
        await self.db.flush()

    # ------------------------------------------------------------------
    # Marketing
    # ------------------------------------------------------------------
    async def _run_marketing(self, base_progress: int) -> None:
        await self._step("marketing", base_progress, "marketing")
        if self._is_done("marketing"):
            return
        chapters = await chapters_service.list_chapters(self.db, self.book.id)
        ctx = self._context()
        result = await MarketerAgent().run(
            ctx,
            subtitle=self.book.subtitle,
            chapter_titles=", ".join(c.title for c in chapters),
        )
        await marketing_service.upsert_kit(self.db, self.book, result.output)  # type: ignore[arg-type]
        await self._record(
            result,
            agent="marketer",
            step_key="marketing",
            input_payload={"book_id": str(self.book.id)},
        )
        self._mark_done("marketing")
        await self.db.flush()

    # ------------------------------------------------------------------
    # Cover job
    # ------------------------------------------------------------------
    async def _run_cover(self) -> None:
        await self._step("cover", 20, "cover")
        ctx = self._context()
        result = await DesignerAgent().run(ctx)
        await self._record(
            result,
            agent="designer",
            step_key="cover.design",
            input_payload={"book_id": str(self.book.id)},
        )
        palette = getattr(result.output, "palette", {}) or {}
        await covers_service.generate_cover(
            self.db,
            self.book,
            palette=palette,
            cover_prompt=getattr(result.output, "cover_prompt", None),
        )
        self._mark_done("cover")

    # ------------------------------------------------------------------
    # Export job
    # ------------------------------------------------------------------
    async def _run_export(self) -> None:
        fmt = (self.job.input_params or {}).get("format", "pdf")
        await self._run_publish(base_progress=50)
        # Ensure the requested format exists even if publish was already done.
        chapters = await chapters_service.list_chapters(self.db, self.book.id)
        export_service = exports_service.ExportService(self.db)
        await export_service.create_and_store(
            self.book,
            chapters,
            fmt=fmt,
            template=(self.book.metadata_json or {}).get("template", "classic"),
            page_size=(self.book.metadata_json or {}).get("page_size", "a5"),
        )
