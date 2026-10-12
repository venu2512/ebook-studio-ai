"""The eight-agent team.

Import the concrete agents and a name -> class registry used by the
orchestrator and the admin UI.
"""

from app.agents.base import AgentContext, AgentResult, BaseAgent, hash_input
from app.agents.designer import DesignerAgent
from app.agents.editor import EditorAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.marketer import MarketerAgent
from app.agents.planner import PlannerAgent
from app.agents.publisher import BookExporter, PublisherAgent
from app.agents.researcher import ResearcherAgent
from app.agents.schemas import (
    BookBible,
    ChapterDraft,
    ChapterPlan,
    Claim,
    DesignOutput,
    EditorOutput,
    FactCheckOutput,
    MarketingOutput,
    OutlineStructure,
    PartPlan,
    PlannerOutput,
    PublisherOutput,
    ResearchNoteOut,
    ResearchOutput,
)
from app.agents.writer import WriterAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "researcher": ResearcherAgent,
    "planner": PlannerAgent,
    "writer": WriterAgent,
    "editor": EditorAgent,
    "fact_checker": FactCheckerAgent,
    "designer": DesignerAgent,
    "marketer": MarketerAgent,
}

# Human-readable pipeline order for the generation UI.
PIPELINE_ORDER: list[str] = [
    "researcher",
    "planner",
    "writer",
    "editor",
    "fact_checker",
    "designer",
    "publisher",
    "marketer",
]

__all__ = [
    "AGENT_REGISTRY",
    "PIPELINE_ORDER",
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "BookBible",
    "BookExporter",
    "ChapterDraft",
    "ChapterPlan",
    "Claim",
    "DesignOutput",
    "DesignerAgent",
    "EditorAgent",
    "EditorOutput",
    "FactCheckOutput",
    "FactCheckerAgent",
    "MarketingOutput",
    "MarketerAgent",
    "OutlineStructure",
    "PartPlan",
    "PlannerAgent",
    "PlannerOutput",
    "PublisherAgent",
    "PublisherOutput",
    "ResearchNoteOut",
    "ResearchOutput",
    "ResearcherAgent",
    "WriterAgent",
    "hash_input",
]
