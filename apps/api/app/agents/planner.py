"""Book Planner agent: outline, title options and word budgets."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import AgentContext, BaseAgent
from app.agents.schemas import PlannerOutput


class PlannerAgent(BaseAgent):
    name: ClassVar[str] = "planner"
    prompt_name: ClassVar[str] = "planner"
    output_model: ClassVar[type[BaseModel]] = PlannerOutput
    temperature: ClassVar[float] = 0.6
    max_tokens: ClassVar[int] = 6000

    def mock_payload(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {
            "topic": ctx.topic,
            "audience": ctx.audience,
            "target_word_count": ctx.target_word_count,
            "chapter_count": ctx.target_chapter_count,
        }

    def quality_issues(self, ctx: AgentContext, output: BaseModel, **kwargs: Any) -> list[str]:
        assert isinstance(output, PlannerOutput)
        issues: list[str] = []
        total = output.total_word_budget or sum(
            c.word_budget for p in output.structure.parts for c in p.chapters
        )
        target = int(kwargs.get("target_word_count") or ctx.target_word_count or 1)
        drift = abs(total - target) / target
        if drift > 0.10:
            issues.append(
                f"Word budgets total {total:,} vs target {target:,} "
                f"({drift:.0%} drift, allowed 10%)."
            )
        titles = [c.title.strip().lower() for p in output.structure.parts for c in p.chapters]
        if len(titles) != len(set(titles)):
            issues.append("Duplicate chapter titles detected.")
        if output.chapter_count == 0:
            issues.append("The outline has no chapters.")
        return issues
