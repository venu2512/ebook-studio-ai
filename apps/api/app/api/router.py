"""Versioned API aggregator.

Every feature router is mounted here and the whole thing is included under
``/api/v1`` by :func:`app.main.create_app`.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    admin,
    auth,
    billing,
    books,
    chapters,
    cover,
    exports,
    files,
    jobs,
    marketing,
    ops,
    outline,
    users,
)

api_router = APIRouter()

# Operational probes first (unauthenticated).
api_router.include_router(ops.router)

# Identity.
api_router.include_router(auth.router)
api_router.include_router(users.router)

# Content: books -> outline -> chapters -> generation -> deliverables.
api_router.include_router(books.router)
api_router.include_router(outline.router)
api_router.include_router(chapters.router)
api_router.include_router(jobs.router)
api_router.include_router(exports.router)
api_router.include_router(cover.router)
api_router.include_router(marketing.router)

# Commerce and administration.
api_router.include_router(billing.router)
api_router.include_router(admin.router)

# Local signed downloads (no-op under S3).
api_router.include_router(files.router)

__all__ = ["api_router"]
