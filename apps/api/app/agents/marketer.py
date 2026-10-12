"""Marketing Specialist agent: description, keywords, social and email copy."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import AgentContext, BaseAgent
from app.agents.schemas import MarketingOutput

# Platform limits we enforce.
KDP_DESCRIPTION_LIMIT = 4000
SHORT_DESCRIPTION_LIMIT = 500
KEYWORD_LIMIT = 7  # Amazon allows 7 keyword slots


class MarketerAgent(BaseAgent):
    name: ClassVar[str] = "marketer"
    prompt_name: ClassVar[str] = "marketer"
    output_model: ClassVar[type[BaseModel]] = MarketingOutput
    temperature: ClassVar[float] = 0.7
    max_tokens: ClassVar[int] = 3000

    def build_context_values(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        values = super().build_context_values(ctx, **kwargs)
        values.setdefault("subtitle", kwargs.get("subtitle") or "")
        values.setdefault("keywords", ", ".join(ctx.extra.get("keywords", [])) or "(none)")
        values.setdefault("chapter_titles", kwargs.get("chapter_titles", ""))
        return values

    def mock_payload(self, ctx: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {
            "title": ctx.title,
            "subtitle": kwargs.get("subtitle") or "",
            "category": ctx.category,
            "keywords": ctx.extra.get("keywords", []),
        }

    def quality_issues(self, ctx: AgentContext, output: BaseModel, **kwargs: Any) -> list[str]:
        assert isinstance(output, MarketingOutput)
        issues: list[str] = []
        if len(output.description) > KDP_DESCRIPTION_LIMIT:
            issues.append("Description exceeds the KDP limit of 4,000 characters.")
        if len(output.short_description) > SHORT_DESCRIPTION_LIMIT:
            issues.append("Short description exceeds 500 characters.")
        if len(output.keywords) > KEYWORD_LIMIT:
            issues.append(f"More than {KEYWORD_LIMIT} keywords; trim for Amazon.")
        banned = ("guaranteed", "100% results", "cure", "risk-free")
        text = (output.description + " " + " ".join(output.bullet_points)).lower()
        hits = [b for b in banned if b in text]
        if hits:
            issues.append(f"Unverifiable/outcome claims present: {', '.join(hits)}.")
        return issues
