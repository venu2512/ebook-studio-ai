"""Designer agent: cover direction, palette, typography and interior template."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import AgentContext, BaseAgent
from app.agents.schemas import DesignOutput


class DesignerAgent(BaseAgent):
    name: ClassVar[str] = "designer"
    prompt_name: ClassVar[str] = "designer"
    output_model: ClassVar[type[BaseModel]] = DesignOutput
    temperature: ClassVar[float] = 0.8
    max_tokens: ClassVar[int] = 2000

    def mock_payload(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {"title": ctx.title, "tone": ctx.tone, "category": ctx.category}

    def quality_issues(self, ctx: AgentContext, output: BaseModel, **kwargs: Any) -> list[str]:
        assert isinstance(output, DesignOutput)
        issues: list[str] = []
        if not output.cover_prompt.strip():
            issues.append("Cover prompt is empty.")
        if not output.palette:
            issues.append("No colour palette was returned.")
        if not output.cover_has_legible_title_at_thumbnail:
            issues.append("Cover title may not be legible at thumbnail size.")
        return issues
