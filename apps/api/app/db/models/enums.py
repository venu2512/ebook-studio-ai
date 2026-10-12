"""Domain enumerations.

Stored as ``VARCHAR`` columns (not native DB enums) so migrations stay simple
and the schema works on both PostgreSQL and SQLite. Pydantic validates the
allowed values at the API boundary.
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class BookStatus(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    WRITING = "writing"
    EDITING = "editing"
    DESIGNING = "designing"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChapterStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    DRAFTED = "drafted"
    EDITED = "edited"
    FACT_CHECKED = "fact_checked"
    APPROVED = "approved"
    FAILED = "failed"


class ChapterVersionSource(StrEnum):
    AGENT = "agent"
    USER = "user"
    RESTORE = "restore"


class JobType(StrEnum):
    FULL_BOOK = "full_book"
    OUTLINE = "outline"
    CHAPTER = "chapter"
    EXPORT = "export"
    COVER = "cover"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRunStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentName(StrEnum):
    RESEARCHER = "researcher"
    PLANNER = "planner"
    WRITER = "writer"
    EDITOR = "editor"
    FACT_CHECKER = "fact_checker"
    DESIGNER = "designer"
    PUBLISHER = "publisher"
    MARKETER = "marketer"


class AssetKind(StrEnum):
    COVER = "cover"
    IMAGE = "image"
    UPLOAD = "upload"


class ExportFormat(StrEnum):
    PDF = "pdf"
    EPUB = "epub"
    DOCX = "docx"


class TemplateKind(StrEnum):
    INTERIOR = "interior"
    COVER = "cover"


class CreditReason(StrEnum):
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    GENERATION = "generation"
    REFUND = "refund"
    GRANT = "grant"
    ADJUSTMENT = "adjustment"


class ClaimVerdict(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    NEEDS_SOURCE = "needs_source"


# Topics that require a disclaimer page and extra caution.
SENSITIVE_CATEGORIES = {
    "health",
    "medical",
    "legal",
    "finance",
    "financial",
    "investing",
    "psychology",
    "therapy",
    "medication",
    "insurance",
}
