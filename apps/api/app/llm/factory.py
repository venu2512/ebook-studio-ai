"""LLM client factory.

The rest of the codebase depends only on :class:`~app.llm.base.LLMClient`.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import AppError
from app.llm.base import LLMClient, LLMMessage, LLMResponse
from app.llm.mock import MockLLM
from app.llm.openai_compat import OpenAICompatibleLLM


def build_llm_client() -> LLMClient:
    """Construct the configured LLM client."""
    settings = get_settings()
    if settings.llm_provider == "mock":
        return MockLLM()
    if settings.llm_provider == "openai_compatible":
        if not settings.llm_api_key:
            raise AppError(
                "LLM_PROVIDER is openai_compatible but LLM_API_KEY is not set.",
                code="llm_not_configured",
                status_code=500,
            )
        return OpenAICompatibleLLM(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            default_timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    raise AppError(f"Unknown LLM provider: {settings.llm_provider}", code="llm_not_configured")


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
