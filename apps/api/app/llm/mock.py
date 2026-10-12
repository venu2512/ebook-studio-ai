"""Deterministic mock LLM provider.

Purpose
-------
Lets the entire product run end to end with **no API key and no network**:
local development, the demo, and the test suite. It synthesises schema-valid
output for each agent task from a small context payload.

Every response is clearly synthetic. This provider is never used when
``LLM_PROVIDER`` is a real one.

TODO(real-provider): the prose is templated filler, not researched writing.
It exists so length/quality gates can be exercised deterministically.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.llm.base import LLMClient, LLMMessage, LLMResponse
from app.llm.tokens import estimate_message_tokens, estimate_tokens


class MockLLM(LLMClient):
    """Returns canned but schema-valid structures keyed by ``task``."""

    provider = "mock"

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
        payload = mock_payload or {}
        data = self._synthesise(task or "generic", payload)
        content = json.dumps(data, ensure_ascii=False, indent=2)

        prompt_tokens = estimate_message_tokens([m.as_tuple() for m in messages])
        completion_tokens = estimate_tokens(content)
        return LLMResponse(
            content=content,
            model=model or "mock",
            provider=self.provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason="stop",
            latency_ms=int((time.perf_counter() - started) * 1000),
            raw={"mock": True, "task": task},
        )

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------
    def _synthesise(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        base = task.split(".")[0]
        handler = {
            "researcher": self._researcher,
            "planner": self._planner,
            "writer": self._writer,
            "editor": self._editor,
            "fact_checker": self._fact_checker,
            "designer": self._designer,
            "marketer": self._marketer,
        }.get(base)
        if handler is None:
            return {"ok": True, "task": task, "note": "mock response"}
        return handler(payload)

    # -- researcher -----------------------------------------------------
    def _researcher(self, payload: dict[str, Any]) -> dict[str, Any]:
        topic = payload.get("topic", "the topic")
        audience = payload.get("audience", "general readers")
        notes = [
            {
                "query": f"What foundational ideas does {audience} need about {topic}?",
                "finding": (
                    f"[MOCK] A widely accepted framing of {topic} starts with the core "
                    "vocabulary, then moves to practical application. No specific external "
                    "statistic is asserted here."
                ),
                "source_url": "https://example.org/mock-reference-1",
                "source_title": "Mock Reference: Foundations",
                "confidence": 0.6,
                "is_verified": False,
                "tags": ["foundations"],
            },
            {
                "query": f"Common mistakes and misconceptions in {topic}?",
                "finding": (
                    "[MOCK] Beginners often skip practice and over-index on theory. "
                    "Errors cluster around applying techniques out of order."
                ),
                "source_url": "https://example.org/mock-reference-3",
                "source_title": "Mock Reference: Common Pitfalls",
                "confidence": 0.4,
                "is_verified": False,
                "tags": ["pitfalls"],
            },
            {
                "query": f"Where does existing material on {topic} fall short?",
                "finding": (
                    "[MOCK] Most available guides are either too theoretical or too shallow. "
                    "There is room for a structured, practical walkthrough."
                ),
                "source_url": "https://example.org/mock-reference-2",
                "source_title": "Mock Reference: Market Landscape",
                "confidence": 0.5,
                "is_verified": False,
                "tags": ["gap"],
            },
        ]
        return {
            "key_themes": ["foundations", "practice", "pitfalls", "application"],
            "notes": notes,
            "competitor_analysis": (
                f"[MOCK] Existing {topic} books tend to be either reference-heavy or "
                "motivational. This book differentiates with a step-by-step structure."
            ),
            "gap_analysis": "A concise, action-oriented treatment with checklists and examples.",
            "unverified_flags": ["No primary sources were retrieved for this mock run."],
        }

    # -- planner --------------------------------------------------------
    def _planner(self, payload: dict[str, Any]) -> dict[str, Any]:
        topic = payload.get("topic", "The Topic")
        audience = payload.get("audience", "readers")
        target_words = int(payload.get("target_word_count", 10000))
        chapter_count = max(3, int(payload.get("chapter_count", 8)))

        # Distribute the word budget across chapters (+/- 10% gate).
        per = target_words // chapter_count
        budgets = [per] * chapter_count
        budgets[0] += target_words - sum(budgets)  # absorb remainder

        parts = [{"title": "Part I: Foundations", "chapters": []}]
        midway = chapter_count // 2
        for i in range(chapter_count):
            if i == midway and chapter_count > 3:
                parts.append({"title": "Part II: Application", "chapters": []})
            target_part = parts[-1] if i >= midway and chapter_count > 3 else parts[0]
            target_part["chapters"].append(
                {
                    "title": self._chapter_title(topic, i),
                    "summary": (
                        f"Chapter {i + 1} explains a focused aspect of {topic} for {audience}, "
                        "with a worked example and a short recap."
                    ),
                    "key_points": [
                        "Define the concept in plain language",
                        "Show a concrete example",
                        "Give an actionable checklist",
                    ],
                    "word_budget": budgets[i],
                }
            )

        return {
            "title": f"{topic}: A Practical Guide",
            "subtitle": f"A step-by-step handbook for {audience}",
            "title_options": [
                f"{topic}: A Practical Guide",
                f"The {topic} Handbook",
                f"Mastering {topic}, One Step at a Time",
            ],
            "reader_promise": (
                f"By the last page, {audience} will be able to apply {topic} "
                "confidently using a repeatable process."
            ),
            "structure": {"parts": parts},
            "total_word_budget": sum(budgets),
        }

    @staticmethod
    def _chapter_title(topic: str, index: int) -> str:
        words = topic.split()
        short = " ".join(words[:4]) if words else "The Subject"
        templates = [
            f"Getting Started with {short}",
            f"The Core Principles of {short}",
            f"Setting Up for Success",
            f"Common Mistakes and How to Avoid Them",
            f"A Practical Walkthrough",
            f"Tools and Techniques",
            f"Scaling and Sustaining Your Results",
            f"Putting It All Together",
            f"Advanced Patterns",
            f"Building Your Own System",
        ]
        return templates[index % len(templates)]

    # -- writer ---------------------------------------------------------
    def _writer(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = payload.get("chapter_title", "Chapter")
        target = int(payload.get("target_word_count", 1500))
        key_points = payload.get("key_points") or [
            "Define the concept",
            "Show an example",
            "Give a checklist",
        ]
        markdown = self._prose(title, target, key_points)
        return {
            "title": title,
            "markdown": markdown,
            "summary": f"{title} covers {', '.join(key_points[:3])}.",
            "key_points": key_points,
            "word_count": len(markdown.split()),
        }

    @staticmethod
    def _prose(title: str, target_words: int, key_points: list[str]) -> str:
        """Deterministic filler prose that respects a word budget."""
        intro = (
            f"## {title}\n\n"
            "This chapter is a synthetic draft produced by the mock model so the "
            "pipeline can be exercised without an API key. It follows the required "
            "structure and roughly matches the word budget.\n\n"
        )
        paragraph = (
            "When you work through {point} in practice, keep the scope small and repeatable. "
            "Start with the simplest version that works, note what happened, and adjust one "
            "variable at a time. Consistency beats intensity, and a short daily habit will "
            "outperform an occasional long session. Write down what you learn so the next "
            "attempt is easier than the last.\n\n"
        )
        sections: list[str] = [intro]
        words = len(intro.split())
        i = 0
        while words < target_words:
            point = key_points[i % len(key_points)] if key_points else "the core idea"
            sections.append(f"### {point.title()}\n\n")
            words += 2
            # Two paragraphs per section.
            for _ in range(2):
                body = paragraph.format(point=point.lower())
                sections.append(body)
                words += len(body.split())
                if words >= target_words:
                    break
            i += 1
        sections.append(
            "### Key takeaways\n\n"
            "- Keep the first step small and concrete.\n"
            "- Review your notes weekly and remove what did not work.\n"
            "- Share the result so you can spot gaps in your own understanding.\n"
        )
        return "".join(sections)

    # -- editor ---------------------------------------------------------
    def _editor(self, payload: dict[str, Any]) -> dict[str, Any]:
        markdown = payload.get("markdown", "")
        # Tighten obvious filler without inventing content.
        edited = markdown.replace("very ", "").replace("really ", "")
        return {
            "markdown": edited,
            "change_notes": [
                "Removed filler intensifiers (very, really).",
                "Standardised heading capitalisation.",
                "Confirmed a consistent second-person voice.",
            ],
            "readability_target_met": True,
            "repetition_removed": True,
            "filler_removed": True,
            "consistency_notes": "Voice is consistent with the style guide.",
        }

    # -- fact checker ---------------------------------------------------
    def _fact_checker(self, payload: dict[str, Any]) -> dict[str, Any]:
        markdown = payload.get("markdown", "")
        claims: list[dict[str, Any]] = []
        # Only flag sentences that look like quantitative claims.
        for sentence in _sentences(markdown):
            lowered = sentence.lower()
            if any(token in lowered for token in ("%", "percent", "study", "research shows")):
                claims.append(
                    {
                        "claim": sentence.strip(),
                        "verdict": "needs_source",
                        "note": "Numeric/attribution claim without a cited source.",
                        "correction": "Rephrase as a general principle or add a real source.",
                    }
                )
        sensitive = bool(payload.get("is_sensitive"))
        return {
            "claims": claims,
            "unsupported_count": sum(1 for c in claims if c["verdict"] == "unsupported"),
            "needs_source_count": sum(1 for c in claims if c["verdict"] == "needs_source"),
            "sensitive_flags": (
                ["Sensitive topic: verify all advice and keep the disclaimer page."]
                if sensitive
                else []
            ),
            "require_disclaimer": sensitive,
            "summary": "No unsupported statistics or quotes were detected in this mock pass.",
            "corrected_markdown": markdown,
        }

    # -- designer -------------------------------------------------------
    def _designer(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = payload.get("title", "Untitled")
        tone = payload.get("tone", "modern")
        return {
            "cover_prompt": (
                f"Minimalist book cover for '{title}', {tone} tone, bold readable "
                "title, generous negative space, limited palette, no text artifacts."
            ),
            "palette": {
                "primary": "#1F2937",
                "accent": "#F59E0B",
                "background": "#F9FAFB",
                "text": "#111827",
            },
            "typography": {"heading": "Inter", "body": "Source Serif 4", "scale": 1.25},
            "interior_template": "classic",
            "image_suggestions": [
                "Chapter opener abstract line art",
                "Process diagram for the walkthrough chapter",
            ],
            "cover_has_legible_title_at_thumbnail": True,
        }

    # -- marketer -------------------------------------------------------
    def _marketer(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = payload.get("title", "Untitled")
        subtitle = payload.get("subtitle") or ""
        category = payload.get("category", "General")
        keywords = payload.get("keywords") or ["guide", "how to", "practical"]
        return {
            "description": (
                f"{title} is a practical, step-by-step guide for readers who want results "
                "without wading through theory. " + (f"{subtitle}. " if subtitle else "") +
                "Each chapter ends with a checklist so you can act immediately."
            ),
            "short_description": f"A practical guide: {title}.",
            "keywords": list(dict.fromkeys([*keywords, "handbook", "step by step"]))[:10],
            "categories": [category, "Self-Help"],
            "kdp_categories": [f"Books > {category}", "Kindle Store > Self-Help"],
            "bullet_points": [
                "A repeatable process you can start today",
                "Checklists at the end of every chapter",
                "Plain-language explanations with worked examples",
                "No hype, no manufactured urgency, and no unrealistic promises",
            ],
            "social_posts": [
                {"platform": "twitter", "text": f"New guide: {title}. Practical steps, zero fluff."},
                {"platform": "linkedin", "text": f"I wrote {title} for people who want a clear process."},
                {"platform": "instagram", "text": f"Just published: {title} 📘"},
            ],
            "email_sequence": [
                {
                    "day": 1,
                    "subject": f"{title} is live",
                    "body": "Hi — my new book is out. Here's what it covers and who it's for.",
                },
                {
                    "day": 3,
                    "subject": "The one chapter to start with",
                    "body": "If you only read one chapter, start with the walkthrough.",
                },
                {
                    "day": 6,
                    "subject": "A quick win from the book",
                    "body": "Here's a checklist you can use this week.",
                },
            ],
            "author_bio": "A practitioner who writes practical, no-hype guides.",
        }


def _sentences(text: str) -> list[str]:
    import re

    parts = re.split(r"(?<=[.!?])\s+", text or "")
    return [p for p in parts if len(p.split()) >= 6]
