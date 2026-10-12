"""ORM model registry.

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and ``create_all`` see the full schema.
"""

from app.db.models.asset import Asset
from app.db.models.billing import CreditTransaction, Subscription
from app.db.models.book import Book, BookOutline
from app.db.models.chapter import Chapter, ChapterVersion
from app.db.models.enums import (
    AgentName,
    AgentRunStatus,
    AssetKind,
    BookStatus,
    ChapterStatus,
    ChapterVersionSource,
    ClaimVerdict,
    CreditReason,
    ExportFormat,
    JobStatus,
    JobType,
    Plan,
    TemplateKind,
    UserRole,
)
from app.db.models.export import Export
from app.db.models.job import AgentRun, Job
from app.db.models.marketing import MarketingKit
from app.db.models.research import ResearchNote
from app.db.models.template import Template
from app.db.models.user import User

__all__ = [
    "AgentName",
    "AgentRun",
    "AgentRunStatus",
    "Asset",
    "AssetKind",
    "Book",
    "BookOutline",
    "BookStatus",
    "Chapter",
    "ChapterStatus",
    "ChapterVersion",
    "ChapterVersionSource",
    "ClaimVerdict",
    "CreditReason",
    "CreditTransaction",
    "Export",
    "ExportFormat",
    "Job",
    "JobStatus",
    "JobType",
    "MarketingKit",
    "Plan",
    "ResearchNote",
    "Subscription",
    "Template",
    "TemplateKind",
    "User",
    "UserRole",
]
