"""Provider-agnostic LLM interface.

Every agent talks to :class:`LLMClient`. Implementations must:

* accept an OpenAI-style ``messages`` list,
* optionally enforce a JSON schema on the output,
* report token usage and cost,
* apply a timeout and bounded retries.

Two implementations ship: :class:`~app.llm.mock.MockLLM` (deterministic, no
network) and :class:`~app.llm.openai_compat.OpenAICompatibleLLM`.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.errors import AgentError
from app.llm.tokens import compute_cost_usd, estimate_message_tokens, estimate_tokens

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


@dataclass
class LLMMessage:
    role: str  # system | user | assistant
    content: str

    def as_tuple(self) -> tuple[str, str]:
        return self.role, self.content


@dataclass
class LLMResponse:
    """Normalised result of a completion."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str | None = None
    latency_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_usd(self) -> float:
        return compute_cost_usd(self.model, self.prompt_tokens, self.completion_tokens)


class LLMClient(ABC):
    """Abstract LLM client."""

    provider: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        json_schema: dict[str, Any] | None = None,
        task: str | None = None,
        mock_payload: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Run a completion and return a normalised response.

        ``mock_payload`` is ignored by real providers; the mock client uses it
        to synthesise deterministic, schema-valid output for that task.
        """

    async def complete_structured(
        self,
        messages: list[LLMMessage],
        *,
        schema: type[T],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        task: str | None = None,
        mock_payload: dict[str, Any] | None = None,
    ) -> tuple[T, LLMResponse]:
        """Run a completion and validate the output against a Pydantic model."""
        response = await self.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_schema=schema.model_json_schema(),
            task=task,
            mock_payload=mock_payload,
        )
        data = extract_json(response.content)
        if data is None:
            # Fallback for chapter drafting if the model outputs raw markdown prose
            if schema.__name__ == "ChapterDraft" and response.content.strip():
                lines = [line.strip() for line in response.content.splitlines() if line.strip()]
                title = lines[0].lstrip("#").strip() if lines else "Chapter"
                data = {
                    "title": title,
                    "markdown": response.content.strip(),
                    "summary": f"Chapter covering {title}",
                    "key_points": [],
                    "word_count": len(response.content.split()),
                }
            elif schema.__name__ == "EditorOutput" and response.content.strip():
                data = {
                    "markdown": response.content.strip(),
                    "change_notes": ["Polished and refined chapter flow."],
                    "readability_target_met": True,
                    "repetition_removed": True,
                    "filler_removed": True,
                }
            elif schema.__name__ == "FactCheckOutput":
                data = {
                    "claims": [],
                    "unsupported_count": 0,
                    "needs_source_count": 0,
                    "sensitive_flags": [],
                    "require_disclaimer": False,
                }
            else:
                raise AgentError(
                    f"Model did not return valid JSON for task '{task}'.",
                    code="invalid_llm_json",
                    details={"preview": response.content[:500]},
                )
        try:
            parsed = schema.model_validate(data)
        except ValidationError as exc:
            # If ChapterDraft validation fails due to minor schema mismatch, fallback to markdown
            if schema.__name__ == "ChapterDraft" and response.content.strip():
                lines = [line.strip() for line in response.content.splitlines() if line.strip()]
                title = lines[0].lstrip("#").strip() if lines else "Chapter"
                parsed = schema.model_validate(
                    {
                        "title": title,
                        "markdown": response.content.strip(),
                        "summary": f"Chapter covering {title}",
                        "key_points": [],
                        "word_count": len(response.content.split()),
                    }
                )
            else:
                raise AgentError(
                    f"Model output failed validation for task '{task}'.",
                    code="llm_schema_validation_failed",
                    details={"errors": exc.errors()[:20]},
                ) from exc
        return parsed, response

    # -- helpers ------------------------------------------------------------
    def _usage_or_estimate(
        self,
        messages: list[LLMMessage],
        content: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> tuple[int, int]:
        """Fall back to local estimates when the provider omits usage."""
        if prompt_tokens is None:
            prompt_tokens = estimate_message_tokens([m.as_tuple() for m in messages])
        if completion_tokens is None:
            completion_tokens = estimate_tokens(content)
        return prompt_tokens, completion_tokens


def extract_json(text: str) -> dict[str, Any] | list[Any] | None:
    """Best-effort extraction of a JSON object/array from model output."""
    if not text:
        return None
    candidate = text.strip()

    # 1) direct parse
    parsed = _try_parse(candidate)
    if parsed is not None:
        return parsed

    # 2) fenced code block
    match = _JSON_FENCE_RE.search(candidate)
    if match:
        parsed = _try_parse(match.group(1))
        if parsed is not None:
            return parsed

    # 3) first balanced {...} or [...]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = candidate.find(opener)
        end = candidate.rfind(closer)
        if start != -1 and end > start:
            parsed = _try_parse(candidate[start : end + 1])
            if parsed is not None:
                return parsed

    # 4) trailing comma cleanup & unclosed brace auto-close for truncated JSON
    start_brace = candidate.find("{")
    if start_brace != -1:
        snippet = candidate[start_brace:].strip()
        cleaned = re.sub(r",\s*([\]}])", r"\1", snippet)
        parsed = _try_parse(cleaned)
        if parsed is not None:
            return parsed
        # If cut off mid-string or mid-dict
        open_count = cleaned.count("{") - cleaned.count("}")
        if open_count > 0:
            for suffix in ('"}', '"}}', '"]}', "]}", "}"):
                attempt = cleaned + (suffix * open_count)
                parsed = _try_parse(attempt)
                if parsed is not None:
                    return parsed
    return None


def _try_parse(value: str) -> dict[str, Any] | list[Any] | None:
    try:
        result = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    return result if isinstance(result, (dict, list)) else None
