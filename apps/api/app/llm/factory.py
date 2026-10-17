"""LLM client factory.

The rest of the codebase depends only on :class:`~app.llm.base.LLMClient`.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings, resolve_llm_base_url
from app.core.errors import AppError
from app.llm.base import LLMClient, LLMMessage, LLMResponse
from app.llm.mock import MockLLM
from app.llm.openai_compat import OpenAICompatibleLLM


def build_llm_client(
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> LLMClient:
    """Construct an LLM client, defaulting to process configuration."""
    settings = get_settings()
    active_provider = provider or settings.llm_provider

    if active_provider == "mock":
        return MockLLM()

    if active_provider in ("openai_compatible", "nvidia", "ollama", "local"):
        resolved_url = base_url or resolve_llm_base_url(active_provider, settings.llm_base_url)
        resolved_key = api_key if api_key is not None else settings.llm_api_key

        # Local LLMs (Ollama, LM Studio, etc.) do not require an API key
        if active_provider in ("ollama", "local"):
            resolved_key = resolved_key or "local"
        elif not resolved_key:
            raise AppError(
                f"LLM_PROVIDER is {active_provider} but LLM_API_KEY is not set.",
                code="llm_not_configured",
                status_code=500,
            )

        return OpenAICompatibleLLM(
            base_url=resolved_url,
            api_key=resolved_key,
            default_timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    raise AppError(f"Unknown LLM provider: {active_provider}", code="llm_not_configured")


@lru_cache
def get_llm_client() -> LLMClient:
    """Process-wide LLM client singleton."""
    return build_llm_client()


__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMResponse",
    "MockLLM",
    "OpenAICompatibleLLM",
    "build_llm_client",
    "get_llm_client",
]
