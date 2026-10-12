"""Writer agent: drafts one chapter at a time."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import AgentContext, BaseAgent
from app.agents.schemas import ChapterDraft


class WriterAgent(BaseAgent):
    name: ClassVar[str] = "writer"
    prompt_name: ClassVar[str] = "writer"
    output_model: ClassVar[type[BaseModel]] = ChapterDraft
    temperature: ClassVar[float] = 0.75
    max_tokens: ClassVar[int] = 8000

    def build_context_values(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        values = super().build_context_values(ctx, **kwargs)
        values.setdefault("previous_summary", "(this is the first chapter)")
        return values

    def mock_payload(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {
            "chapter_title": kwargs.get("chapter_title", "Chapter"),
            "target_word_count": int(kwargs.get("target_word_count", 1500)),
            "key_points": kwargs.get("key_points") or [],
        }

    def quality_issues(
        self, ctx: AgentContext, output: BaseModel, **kwargs: Any
    ) -> list[str]:
        assert isinstance(output, ChapterDraft)
        issues: list[str] = []
        words = len(output.markdown.split())
        target = int(kwargs.get("target_word_count") or 0)
        if target and abs(words - target) / max(target, 1) > 0.15:
            issues.append(
                f"Chapter is {words:,} words vs a {target:,}-word budget "
                "(-/+15% allowed)."
            )
        if not output.markdown.strip():
            issues.append("Chapter markdown is empty.")
        if "##" not in output.markdown:
            issues.append("Chapter has no headings.")
        # Guard against fabricated citations in the raw draft.
        lowered = output.markdown.lower()
        if any(p in lowered for p in ("according to a study", "research shows that", "studies show")):
            issues.append("Draft contains attribution-style claims that need verification.")
        return issues
