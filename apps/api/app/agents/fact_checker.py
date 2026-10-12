"""Fact Checker agent: verifies claims and flags sensitive content."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import AgentContext, BaseAgent
from app.agents.schemas import FactCheckOutput


class FactCheckerAgent(BaseAgent):
    name: ClassVar[str] = "fact_checker"
    prompt_name: ClassVar[str] = "fact_checker"
    output_model: ClassVar[type[BaseModel]] = FactCheckOutput
    temperature: ClassVar[float] = 0.2
    max_tokens: ClassVar[int] = 4000

    def build_context_values(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        values = super().build_context_values(ctx, **kwargs)
        values.setdefault("chapter_title", kwargs.get("chapter_title", "Chapter"))
        values.setdefault("edited_markdown", kwargs.get("markdown", ""))
        return values

    def mock_payload(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {
            "markdown": kwargs.get("markdown", ""),
            "is_sensitive": ctx.is_sensitive,
        }

    def quality_issues(self, ctx: AgentContext, output: BaseModel, **kwargs: Any) -> list[str]:
        assert isinstance(output, FactCheckOutput)
        issues: list[str] = []
        open_claims = [c for c in output.claims if c.verdict in {"unsupported", "needs_source"}]
        if open_claims:
            issues.append(
                f"{len(open_claims)} claim(s) are unsupported or need a source and were "
                "flagged in the chapter rather than removed silently."
            )
        if ctx.is_sensitive and not output.require_disclaimer:
            issues.append("Sensitive topic: a disclaimer must be required.")
        if output.sensitive_flags:
            issues.extend(output.sensitive_flags)
        return issues
