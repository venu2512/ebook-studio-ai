"""OpenAI-compatible chat-completions client.

Works with any provider that speaks the OpenAI ``/chat/completions`` shape:
OpenAI, OpenRouter, Groq, Together, Fireworks, vLLM, Ollama, LM Studio, ...

Built-in protections: request timeout, bounded retries with exponential
backoff on transient failures, and structured-output support (the JSON schema
is passed both as a system instruction and, where supported, via
``response_format``).
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.llm.base import LLMClient, LLMMessage, LLMResponse

log = get_logger(__name__)


class _TransientError(Exception):
    """Raised internally for retryable upstream failures."""


class OpenAICompatibleLLM(LLMClient):
    provider = "openai_compatible"

    def __init__(
        self, *, base_url: str, api_key: str, default_timeout: int, max_retries: int
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_timeout = default_timeout
        self.max_retries = max_retries

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
        started = time.perf_counter()
        wire_messages = [{"role": m.role, "content": m.content} for m in messages]

        if json_schema is not None:
            wire_messages.append(
                {
                    "role": "system",
                    "content": (
                        "Respond with a single JSON object that validates against this "
                        "JSON Schema. Do not include markdown fences or commentary.\n"
                        + json.dumps(json_schema)
                    ),
                }
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": wire_messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if json_schema is not None:
            # Broadly supported; providers that reject it will error clearly.
            payload["response_format"] = {"type": "json_object"}

        data = await self._post_with_retries(payload)
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}

        prompt_tokens, completion_tokens = self._usage_or_estimate(
            messages,
            content,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )

        return LLMResponse(
            content=content,
            model=data.get("model") or model,
            provider=self.provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=choice.get("finish_reason"),
            latency_ms=int((time.perf_counter() - started) * 1000),
            raw={"id": data.get("id")},
        )

    async def _post_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        timeout = httpx.Timeout(self.default_timeout, connect=15.0)
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key and self.api_key not in ("local", "local-no-key", "none"):
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.base_url}/chat/completions"

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=20),
                retry=retry_if_exception_type(_TransientError),
                reraise=True,
            ):
                with attempt:
                    return await self._post_once(url, headers, payload, timeout)
        except httpx.HTTPError as exc:
            raise ProviderError(
                "Could not reach the model provider.", details={"reason": str(exc)}
            ) from exc
        except _TransientError as exc:
            raise ProviderError(
                "The model provider kept failing after retries.", details={"reason": str(exc)}
            ) from exc

        raise ProviderError("The model provider returned no response.")  # pragma: no cover

    async def _post_once(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        request_timeout: httpx.Timeout,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code in (429, 500, 502, 503, 504):
            log.warning("llm_transient_error", status=response.status_code)
            raise _TransientError(f"HTTP {response.status_code}")
        if response.status_code == 400 and "response_format" in payload:
            err_text = response.text.lower()
            if "response_format" in err_text or "json_object" in err_text:
                log.info("llm_response_format_unsupported_retrying_without_it")
                fallback_payload = dict(payload)
                fallback_payload.pop("response_format", None)
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    fb_res = await client.post(url, headers=headers, json=fallback_payload)
                    if fb_res.status_code < 400:
                        return fb_res.json()
        if response.status_code >= 400:
            raise ProviderError(
                f"Provider returned HTTP {response.status_code}.",
                details={"body": response.text[:1000]},
            )
        return response.json()


__all__ = ["OpenAICompatibleLLM", "get_settings"]
