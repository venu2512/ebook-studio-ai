"""Marketing kit schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class MarketingKitRead(ORMModel):
    id: uuid.UUID
    book_id: uuid.UUID
    description: str | None
    short_description: str | None
    keywords: list[str]
    categories: list[str]
    kdp_categories: list[str]
    bullet_points: list[str]
    social_posts: list[dict[str, Any]]
    email_sequence: list[dict[str, Any]]
    author_bio: str | None
    created_at: datetime
