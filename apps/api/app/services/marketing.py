"""Marketing kit persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import MarketingOutput
from app.db.models import Book, MarketingKit


async def get_kit(db: AsyncSession, book_id: object) -> MarketingKit | None:
    result = await db.execute(select(MarketingKit).where(MarketingKit.book_id == book_id))
    return result.scalar_one_or_none()


async def upsert_kit(db: AsyncSession, book: Book, output: MarketingOutput) -> MarketingKit:
    """Create or update the book's marketing kit from agent output."""
    kit = await get_kit(db, book.id)
    if kit is None:
        kit = MarketingKit(book_id=book.id)
        db.add(kit)

    kit.description = output.description
    kit.short_description = output.short_description
    kit.keywords = output.keywords
    kit.categories = output.categories
    kit.kdp_categories = output.kdp_categories
    kit.bullet_points = output.bullet_points
    kit.social_posts = [p.model_dump() for p in output.social_posts]
    kit.email_sequence = [e.model_dump() for e in output.email_sequence]
    kit.author_bio = output.author_bio

    # Mirror onto the book for listing/search surfaces.
    book.description = output.description
    if output.keywords:
        book.keywords = output.keywords
    await db.flush()
    return kit
