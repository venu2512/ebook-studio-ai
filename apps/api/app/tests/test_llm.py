"""LLM layer: JSON extraction, token accounting and the mock provider."""

from __future__ import annotations

import pytest

from app.agents.schemas import (
    ChapterDraft,
    DesignOutput,
    EditorOutput,
    FactCheckOutput,
    MarketingOutput,
    PlannerOutput,
    ResearchOutput,
)
from app.core.config import get_settings
from app.llm.base import LLMMessage, extract_json
from app.llm.factory import build_llm_client, get_llm_client
from app.llm.mock import MockLLM
from app.llm.tokens import (
    compute_cost_usd,
    estimate_message_tokens,
    estimate_tokens,
    price_for,
    tokens_to_credits,
)


# ---------------------------------------------------------------------------
# extract_json
# ---------------------------------------------------------------------------
def test_extract_json_direct_object():
    assert extract_json('{"a": 1, "b": [2, 3]}') == {"a": 1, "b": [2, 3]}


def test_extract_json_fenced_block():
    text = 'Here you go:\n```json\n{"title": "x"}\n```\nDone.'
    assert extract_json(text) == {"title": "x"}


def test_extract_json_embedded_object():
    assert extract_json('prefix {"ok": true} suffix') == {"ok": True}


def test_extract_json_array():
    assert extract_json("[1, 2, 3]") == [1, 2, 3]


@pytest.mark.parametrize("text", ["", "   ", "not json at all", "{broken"])
def test_extract_json_returns_none_for_garbage(text):
    assert extract_json(text) is None


# ---------------------------------------------------------------------------
# Token accounting
# ---------------------------------------------------------------------------
def test_estimate_tokens_scales_with_length():
    assert estimate_tokens("") == 0
    short = estimate_tokens("hello world")
    long = estimate_tokens("hello world " * 100)
    assert 1 <= short < long


def test_estimate_message_tokens_adds_overhead():
    messages = [("system", "You are helpful."), ("user", "Hi")]
    assert estimate_message_tokens(messages) > estimate_tokens("You are helpful.")


def test_price_lookup_and_cost():
    assert price_for("gpt-4o-mini") == (0.15, 0.60)
    # Dated snapshots resolve by prefix.
    assert price_for("gpt-4o-2024-08-06") == (2.50, 10.00)
    # Unknown models fall back to a conservative default.
    assert price_for("totally-made-up")[0] > 0
    # The mock model is free.
    assert compute_cost_usd("mock", 10_000, 10_000) == 0.0
    assert compute_cost_usd("gpt-4o", 1_000_000, 0) == 2.50


def test_tokens_to_credits():
    assert tokens_to_credits(0) == 0
    assert tokens_to_credits(1) == 1
    assert tokens_to_credits(1500) == 2  # ceil(1.5)


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------
def test_factory_returns_mock_in_tests():
    assert get_settings().llm_provider == "mock"
    client = build_llm_client()
    assert isinstance(client, MockLLM)
    assert get_llm_client() is get_llm_client()  # cached singleton


# ---------------------------------------------------------------------------
# Mock provider synthesises schema-valid output for every task
# ---------------------------------------------------------------------------
async def _structured(task: str, schema, payload: dict):
    client = MockLLM()
    messages = [LLMMessage(role="system", content="sys"), LLMMessage(role="user", content="go")]
    parsed, response = await client.complete_structured(
        messages, schema=schema, model="mock", task=task, mock_payload=payload
    )
    return parsed, response


async def test_mock_researcher_schema():
    output, response = await _structured(
        "researcher", ResearchOutput, {"topic": "Bread baking", "audience": "beginners"}
    )
    assert isinstance(output, ResearchOutput)
    assert len(output.notes) >= 3
    assert response.provider == "mock"
    assert response.total_tokens > 0


async def test_mock_planner_schema():
    output, _ = await _structured(
        "planner",
        PlannerOutput,
        {
            "topic": "Bread baking",
            "audience": "beginners",
            "target_word_count": 5000,
            "chapter_count": 5,
        },
    )
    assert output.chapter_count == 5
    assert output.total_word_budget > 0
    assert output.structure.parts


async def test_mock_writer_schema():
    output, _ = await _structured(
        "writer",
        ChapterDraft,
        {"chapter_title": "Start Here", "target_word_count": 300, "key_points": ["A", "B"]},
    )
    assert output.markdown.strip()
    assert "##" in output.markdown
    assert output.summary


async def test_mock_editor_schema():
    output, _ = await _structured(
        "editor",
        EditorOutput,
        {"markdown": "## Title\n\nvery really good text.", "chapter_title": "T"},
    )
    assert output.markdown
    assert "very" not in output.markdown  # filler stripped
    assert output.change_notes


async def test_mock_fact_checker_flags_numeric_claims():
    markdown = "Studies show that 73% of bakers prefer this method every single time."
    output, _ = await _structured(
        "fact_checker", FactCheckOutput, {"markdown": markdown, "is_sensitive": False}
    )
    assert output.claims
    assert output.needs_source_count >= 1


async def test_mock_fact_checker_requires_disclaimer_for_sensitive():
    output, _ = await _structured(
        "fact_checker", FactCheckOutput, {"markdown": "Take this advice.", "is_sensitive": True}
    )
    assert output.require_disclaimer is True
    assert output.sensitive_flags


async def test_mock_designer_schema():
    output, _ = await _structured("designer", DesignOutput, {"title": "T", "tone": "modern"})
    assert output.cover_prompt
    assert output.palette


async def test_mock_marketer_schema():
    output, _ = await _structured(
        "marketer", MarketingOutput, {"title": "T", "category": "Cooking", "keywords": ["bread"]}
    )
    assert output.description
    assert output.keywords
    assert output.social_posts and output.email_sequence


async def test_mock_unknown_task_returns_generic_payload():
    from app.llm.mock import MockLLM as _Mock

    client = _Mock()
    response = await client.complete(
        [LLMMessage(role="user", content="x")], model="mock", task="something.else"
    )
    assert "mock response" in response.content
