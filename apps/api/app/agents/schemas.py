"""Typed inputs and outputs for each agent.

These Pydantic models are the contract between an agent, the LLM (their JSON
schema is sent to the model) and the orchestrator (which persists them).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Communication / style
# ---------------------------------------------------------------------------
class BookBible(BaseModel):
    """Running shared memory passed to every Writer call for consistency."""

    voice: str = "clear, practical, second person"
    audience: str = "general readers"
    language: str = "en"
    tone: str = "conversational"
    style_guide: str = ""
    terminology: dict[str, str] = Field(default_factory=dict)
    chapter_summaries: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Researcher
# ---------------------------------------------------------------------------
class ResearchNoteOut(BaseModel):
    query: str
    finding: str
    source_url: str | None = None
    source_title: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    is_verified: bool = False
    tags: list[str] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    key_themes: list[str] = Field(default_factory=list)
    notes: list[ResearchNoteOut] = Field(default_factory=list)
    competitor_analysis: str = ""
    gap_analysis: str = ""
    unverified_flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------
class ChapterPlan(BaseModel):
    title: str
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    word_budget: int = Field(default=0, ge=0)


class PartPlan(BaseModel):
    title: str
    chapters: list[ChapterPlan] = Field(default_factory=list)


class OutlineStructure(BaseModel):
    parts: list[PartPlan] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    title: str
    subtitle: str | None = None
    title_options: list[str] = Field(default_factory=list)
    reader_promise: str = ""
    structure: OutlineStructure
    total_word_budget: int = 0

    @property
    def chapter_count(self) -> int:
        return sum(len(p.chapters) for p in self.structure.parts)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
class ChapterDraft(BaseModel):
    title: str
    markdown: str
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    word_count: int = 0


# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------
class EditorOutput(BaseModel):
    markdown: str
    change_notes: list[str] = Field(default_factory=list)
    readability_target_met: bool = True
    repetition_removed: bool = True
    filler_removed: bool = True
    consistency_notes: str = ""


# ---------------------------------------------------------------------------
# Fact checker
# ---------------------------------------------------------------------------
class Claim(BaseModel):
    claim: str
    verdict: str = "needs_source"  # supported | unsupported | needs_source
    note: str = ""
    correction: str | None = None


class FactCheckOutput(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    unsupported_count: int = 0
    needs_source_count: int = 0
    sensitive_flags: list[str] = Field(default_factory=list)
    require_disclaimer: bool = False
    summary: str = ""
    corrected_markdown: str | None = None


# ---------------------------------------------------------------------------
# Designer
# ---------------------------------------------------------------------------
class DesignOutput(BaseModel):
    cover_prompt: str
    palette: dict[str, str] = Field(default_factory=dict)
    typography: dict[str, object] = Field(default_factory=dict)
    interior_template: str = "classic"
    image_suggestions: list[str] = Field(default_factory=list)
    cover_has_legible_title_at_thumbnail: bool = True


# ---------------------------------------------------------------------------
# Marketing specialist
# ---------------------------------------------------------------------------
class SocialPost(BaseModel):
    platform: str
    text: str


class EmailStep(BaseModel):
    day: int = 1
    subject: str
    body: str


class MarketingOutput(BaseModel):
    description: str
    short_description: str = ""
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    kdp_categories: list[str] = Field(default_factory=list)
    bullet_points: list[str] = Field(default_factory=list)
    social_posts: list[SocialPost] = Field(default_factory=list)
    email_sequence: list[EmailStep] = Field(default_factory=list)
    author_bio: str = ""


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------
class PublishedArtifact(BaseModel):
    format: str
    storage_key: str
    size_bytes: int = 0
    page_count: int | None = None
    checksum: str = ""
    renderer: str = ""


class PublisherOutput(BaseModel):
    artifacts: list[PublishedArtifact] = Field(default_factory=list)
    validation: dict[str, object] = Field(default_factory=dict)
    has_front_matter: bool = True
    has_toc: bool = True
    has_disclaimer: bool = False
    chapter_count: int = 0
    total_word_count: int = 0
    notes: list[str] = Field(default_factory=list)
