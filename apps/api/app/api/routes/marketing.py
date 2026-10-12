"""Marketing kit routes: read and (re)generate the book's marketing copy."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.agents import MarketerAgent
from app.api.deps import CurrentUser, SessionDep
from app.core.errors import NotFoundError
from app.schemas.marketing import MarketingKitRead
from app.services import books as books_service
from app.services import chapters as chapters_service
from app.services import marketing as marketing_service

router = APIRouter(tags=["marketing"])


async def _require_kit(db, book_id: uuid.UUID) -> object:
    kit = await marketing_service.get_kit(db, book_id)
    if kit is None:
        raise NotFoundError(
            "No marketing kit yet. Generate it once the book is written.",
            code="marketing_not_found",
        )
    return kit


@router.get("/books/{book_id}/marketing", response_model=MarketingKitRead)
async def get_marketing(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> MarketingKitRead:
    await books_service.get_owned_book(db, book_id, user)
    kit = await _require_kit(db, book_id)
    return MarketingKitRead.model_validate(kit)


@router.post("/books/{book_id}/marketing", response_model=MarketingKitRead)
async def regenerate_marketing(
    book_id: uuid.UUID, user: CurrentUser, db: SessionDep
) -> MarketingKitRead:
    """Run the Marketing Specialist and upsert the kit (synchronous)."""
    book = await books_service.get_owned_book(db, book_id, user)
    chapters = await chapters_service.list_chapters(db, book_id)
    ctx = books_service.build_agent_context(book)
    result = await MarketerAgent().run(
        ctx,
        subtitle=book.subtitle,
        chapter_titles=", ".join(c.title for c in chapters),
    )
    kit = await marketing_service.upsert_kit(db, book, result.output)  # type: ignore[arg-type]
    return MarketingKitRead.model_validate(kit)
