"""Cover routes: fetch or (re)generate the book cover.

Cover generation is synchronous: the Designer agent picks a palette and a cover
prompt, then the cover service renders the art (image provider when configured,
otherwise a deterministic text-overlay cover) and stores it as an ``Asset``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.agents import DesignerAgent
from app.api.deps import CurrentUser, SessionDep
from app.db.models import Asset, Book
from app.schemas.export import CoverRead, CoverRegenerateRequest
from app.services import books as books_service
from app.services import covers as covers_service

router = APIRouter(tags=["cover"])


async def _cover_payload(db, book: Book) -> CoverRead:
    design = (book.metadata_json or {}).get("design") or {}
    palette = design.get("palette") or {}
    asset: Asset | None = None
    if book.cover_asset_id:
        asset = await db.get(Asset, book.cover_asset_id)
    return CoverRead(
        asset_id=asset.id if asset else None,
        url=covers_service.asset_url(asset) if asset else None,
        prompt=asset.prompt if asset else design.get("cover_prompt"),
        palette=palette,
    )


@router.get("/books/{book_id}/cover", response_model=CoverRead)
async def get_cover(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> CoverRead:
    book = await books_service.get_owned_book(db, book_id, user)
    return await _cover_payload(db, book)


@router.post("/books/{book_id}/cover", response_model=CoverRead)
async def regenerate_cover(
    book_id: uuid.UUID,
    payload: CoverRegenerateRequest,
    user: CurrentUser,
    db: SessionDep,
) -> CoverRead:
    """Generate a fresh cover, optionally with a user-supplied prompt."""
    book = await books_service.get_owned_book(db, book_id, user)
    ctx = books_service.build_agent_context(book)

    palette: dict[str, str] | None = None
    cover_prompt: str | None = payload.prompt
    if not cover_prompt:
        design = (book.metadata_json or {}).get("design") or {}
        palette = design.get("palette") or None
        cover_prompt = design.get("cover_prompt") or None
    if not cover_prompt:
        result = await DesignerAgent().run(ctx)
        palette = getattr(result.output, "palette", {}) or {}
        cover_prompt = getattr(result.output, "cover_prompt", None)

    await covers_service.generate_cover(db, book, palette=palette, cover_prompt=cover_prompt)
    return await _cover_payload(db, book)


@router.get("/books/{book_id}/assets", response_model=list[dict])
async def list_assets(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> list[dict]:
    """Cover and uploaded images attached to a book."""
    await books_service.get_owned_book(db, book_id, user)
    result = await db.execute(
        select(Asset).where(Asset.book_id == book_id).order_by(Asset.created_at.desc())
    )
    return [
        {
            "id": str(a.id),
            "kind": a.kind,
            "url": covers_service.asset_url(a),
            "mime_type": a.mime_type,
            "size_bytes": a.size_bytes,
            "width": a.width,
            "height": a.height,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]
