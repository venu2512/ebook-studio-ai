"""Researcher agent: gathers themes, sources and gap analysis."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import AgentContext, BaseAgent
from app.agents.schemas import ResearchOutput

MIN_SOURCES = 3


class ResearcherAgent(BaseAgent):
    name: ClassVar[str] = "researcher"
    prompt_name: ClassVar[str] = "researcher"
    output_model: ClassVar[type[BaseModel]] = ResearchOutput
    temperature: ClassVar[float] = 0.5
    max_tokens: ClassVar[int] = 4000

    def mock_payload(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {"topic": ctx.topic, "audience": ctx.audience, "category": ctx.category}

    def quality_issues(self, ctx: AgentContext, output: BaseModel, **kwargs: Any) -> list[str]:
        assert isinstance(output, ResearchOutput)
        issues: list[str] = []
        sourced = [n for n in output.notes if n.source_url]
        if len(sourced) < MIN_SOURCES:
            issues.append(
                f"Only {len(sourced)} sourced notes (target >= {MIN_SOURCES}); "
                "treat findings as unverified."
            )
        if not output.notes:
            issues.append("No research notes were produced.")
        unsourced = [n for n in output.notes if not n.source_url and not n.is_verified]
        if unsourced:
            issues.append(f"{len(unsourced)} note(s) have no source and must not be cited.")
        return issues
