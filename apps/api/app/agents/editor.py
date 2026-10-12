"""Editor agent: improves clarity, removes filler, keeps the voice."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import AgentContext, BaseAgent
from app.agents.schemas import EditorOutput


class EditorAgent(BaseAgent):
    name: ClassVar[str] = "editor"
    prompt_name: ClassVar[str] = "editor"
    output_model: ClassVar[type[BaseModel]] = EditorOutput
    temperature: ClassVar[float] = 0.4
    max_tokens: ClassVar[int] = 8000

    def build_context_values(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        values = super().build_context_values(ctx, **kwargs)
        values.setdefault("chapter_title", "Chapter")
        values.setdefault("draft_markdown", kwargs.get("markdown", ""))
        return values

    def mock_payload(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {"markdown": kwargs.get("markdown", ""), "chapter_title": kwargs.get("chapter_title", "Chapter")}

    def quality_issues(self, ctx: AgentContext, output: BaseModel, **kwargs: Any) -> list[str]:
        assert isinstance(output, EditorOutput)
        issues: list[str] = []
        if not output.markdown.strip():
            issues.append("Edited chapter is empty.")
        if not output.readability_target_met:
            issues.append("Readability target was not met.")
        return issues
