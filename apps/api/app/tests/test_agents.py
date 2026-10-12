"""Agent unit tests: outputs and quality gates.

Everything runs against the deterministic mock LLM, so the assertions are
stable and no network access is required.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.agents import (
    DesignerAgent,
    EditorAgent,
    FactCheckerAgent,
    MarketerAgent,
    PlannerAgent,
    PublisherAgent,
    ResearcherAgent,
    WriterAgent,
)
from app.agents.base import AgentContext, hash_input
from app.agents.schemas import ChapterDraft


def make_ctx(**overrides) -> AgentContext:
    defaults = {
        "book_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "job_id": None,
        "title": "The Bread Book",
        "topic": "Bread baking for beginners",
        "audience": "home cooks",
        "category": "Cooking",
        "language": "en",
        "tone": "conversational",
        "target_word_count": 5000,
        "target_chapter_count": 5,
    }
    defaults.update(overrides)
    return AgentContext(**defaults)


async def test_researcher_passes_quality_gate():
    ctx = make_ctx()
    result = await ResearcherAgent().run(ctx)
    assert result.agent == "researcher"
    assert len(result.output.notes) >= 3
    assert result.issues == []  # mock supplies 3 sourced notes


async def test_planner_word_budget_within_tolerance():
    ctx = make_ctx(target_word_count=5000, target_chapter_count=5)
    result = await PlannerAgent().run(ctx)
    assert result.output.chapter_count == 5
    assert result.issues == []
    titles = [c.title for p in result.output.structure.parts for c in p.chapters]
    assert len(titles) == len(set(titles))


async def test_planner_flags_budget_drift():
    ctx = make_ctx(target_word_count=5000, target_chapter_count=5)
    planner = PlannerAgent()
    result = await planner.run(ctx)
    # Pretend the model returned a wildly different budget than requested.
    issues = planner.quality_issues(ctx, result.output, target_word_count=100_000)
    assert any("drift" in i.lower() for i in issues)


async def test_writer_produces_markdown_with_headings():
    ctx = make_ctx()
    result = await WriterAgent().run(
        ctx,
        chapter_number=1,
        chapter_title="Getting Started",
        chapter_summary="An intro",
        key_points=["Mix", "Bake", "Rest"],
        target_word_count=400,
        previous_summary="(first)",
    )
    draft: ChapterDraft = result.output  # type: ignore[assignment]
    assert draft.markdown.strip()
    assert "##" in draft.markdown
    assert draft.key_points


async def test_writer_quality_gate_flags_short_chapter():
    ctx = make_ctx()
    result = await WriterAgent().run(
        ctx,
        chapter_number=1,
        chapter_title="T",
        chapter_summary="s",
        key_points=["a"],
        target_word_count=400,
        previous_summary="(first)",
    )
    issues = WriterAgent().quality_issues(ctx, result.output, target_word_count=100_000)
    assert any("budget" in i.lower() for i in issues)


async def test_editor_removes_filler():
    ctx = make_ctx()
    result = await EditorAgent().run(
        ctx, chapter_title="T", markdown="## T\n\nThis is very really good."
    )
    assert "very" not in result.output.markdown
    assert result.output.change_notes


async def test_fact_checker_flags_unsourced_claims():
    ctx = make_ctx()
    markdown = "Research shows that 84% of people agree with this statement."
    result = await FactCheckerAgent().run(ctx, chapter_title="T", markdown=markdown)
    assert result.output.claims
    assert result.issues  # at least one open claim is surfaced


async def test_fact_checker_sensitive_topic_requires_disclaimer():
    ctx = make_ctx(category="Health")
    assert ctx.is_sensitive is True
    result = await FactCheckerAgent().run(ctx, chapter_title="T", markdown="Take two.")
    assert result.output.require_disclaimer is True
    assert result.output.sensitive_flags


async def test_designer_returns_palette_and_prompt():
    ctx = make_ctx()
    result = await DesignerAgent().run(ctx)
    assert result.output.cover_prompt
    assert result.output.palette.get("primary")
    assert result.issues == []


async def test_marketer_respects_keyword_limit():
    ctx = make_ctx()
    result = await MarketerAgent().run(ctx, subtitle="A guide", chapter_titles="One, Two")
    assert result.output.description
    assert len(result.output.keywords) <= 7
    assert result.issues == []


# ---------------------------------------------------------------------------
# Publisher agent (no LLM; renders via an injected exporter)
# ---------------------------------------------------------------------------
class _FakeExporter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def render(self, document, fmt: str, *, template: str):
        from app.agents.schemas import PublishedArtifact

        self.calls.append(fmt)
        return PublishedArtifact(
            format=fmt, storage_key=f"{fmt}.out", size_bytes=1234, renderer="fake"
        )


def _fake_document(*, has_disclaimer: bool = False):
    chapters = [
        SimpleNamespace(title="One", markdown="# One\n\ncontent"),
        SimpleNamespace(title="Two", markdown="# Two\n\nmore"),
    ]
    return SimpleNamespace(
        chapters=chapters,
        front_matter="Front matter",
        disclaimer="Disclaimer" if has_disclaimer else "",
        html="<h1>toc</h1>",
        total_word_count=6,
    )


async def test_publisher_renders_all_formats():
    exporter = _FakeExporter()
    result = await PublisherAgent(exporter=exporter).run(
        make_ctx(), document=_fake_document(), formats=["pdf", "epub", "docx"]
    )
    assert exporter.calls == ["pdf", "epub", "docx"]
    assert len(result.output.artifacts) == 3
    assert result.output.chapter_count == 2
    assert result.issues == []


async def test_publisher_flags_missing_disclaimer_for_sensitive_topics():
    result = await PublisherAgent(exporter=_FakeExporter()).run(
        make_ctx(category="Health"), document=_fake_document(has_disclaimer=False)
    )
    assert any("disclaimer" in i.lower() for i in result.issues)


async def test_publisher_flags_no_document():
    result = await PublisherAgent().run(make_ctx(), document=None)
    assert result.output.chapter_count == 0
    assert any("no chapters" in i.lower() for i in result.issues)


def test_hash_input_is_stable_and_order_independent():
    a = hash_input({"b": 2, "a": 1})
    b = hash_input({"a": 1, "b": 2})
    assert a == b
    assert len(a) == 64
