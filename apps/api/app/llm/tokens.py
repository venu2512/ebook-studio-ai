"""Token estimation and cost accounting.

Token counts are estimated client-side (``len(text) / 4`` for English prose) so
we can enforce budgets even when a provider omits usage. Real usage from the
provider always wins when present.

Prices are USD per 1,000,000 tokens and are best-effort reference values -
override them in one place if your provider differs.
"""

from __future__ import annotations

import math
import re

_WORD_RE = re.compile(r"\S+")

# USD per 1M tokens: (input, output)
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "o3-mini": (1.10, 4.40),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-sonnet-4": (3.00, 15.00),
    "llama-3.1-70b": (0.59, 0.79),
    "mock": (0.0, 0.0),
}

# Conservative fallback for unknown models.
DEFAULT_PRICE = (1.00, 3.00)


def estimate_tokens(text: str | None) -> int:
    """Rough token estimate. Never returns less than 1 for non-empty text."""
    if not text:
        return 0
    # Characters/4 is the standard heuristic; word count is a floor.
    by_chars = math.ceil(len(text) / 4)
    by_words = math.ceil(len(_WORD_RE.findall(text)) * 1.33)
    return max(1, by_chars, by_words)


def estimate_message_tokens(messages: list[tuple[str, str]]) -> int:
    """Estimate prompt tokens for a list of ``(role, content)`` pairs."""
    total = 0
    for _role, content in messages:
        total += estimate_tokens(content) + 4  # per-message overhead
    return total + 2


def price_for(model: str) -> tuple[float, float]:
    """Return ``(input_price, output_price)`` per 1M tokens for a model."""
    key = (model or "").lower()
    if key in PRICING:
        return PRICING[key]
    # Match by prefix so dated snapshots (gpt-4o-2024-08-06) still resolve.
    for name, price in PRICING.items():
        if name in key:
            return price
    return DEFAULT_PRICE


def compute_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Compute the USD cost of a call, rounded to 6 decimals."""
    in_price, out_price = price_for(model)
    cost = (prompt_tokens / 1_000_000) * in_price + (completion_tokens / 1_000_000) * out_price
    return round(cost, 6)


def tokens_to_credits(total_tokens: int, credits_per_1k: int = 1) -> int:
    """Convert tokens to credits, always charging at least 1 for any usage."""
    if total_tokens <= 0:
        return 0
    return max(1, math.ceil(total_tokens / 1000) * max(1, credits_per_1k))
