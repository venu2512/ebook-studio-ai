"""Simple sliding-window rate limiter.

In-memory by default (single process). TODO(scale): back this with Redis
(``INCR`` + ``EXPIRE``) so limits are shared across API replicas.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import RateLimitError

_HITS: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int) -> None:
    """Raise :class:`RateLimitError` when the caller exceeds ``limit`` hits."""
    key = f"{bucket}:{_client_key(request)}"
    now = time.monotonic()
    hits = _HITS[key]
    while hits and now - hits[0] > window_seconds:
        hits.popleft()
    if len(hits) >= limit:
        retry_after = int(window_seconds - (now - hits[0])) + 1
        raise RateLimitError(
            "Too many requests. Please try again shortly.",
            details={"retry_after_seconds": retry_after},
        )
    hits.append(now)


def rate_limit(bucket: str, limit: int, window_seconds: int):
    """Dependency factory: ``Depends(rate_limit("auth", 10, 60))``."""

    def _dependency(request: Request) -> None:
        check_rate_limit(request, bucket, limit, window_seconds)

    return _dependency


def reset_rate_limits() -> None:
    """Test helper."""
    _HITS.clear()
