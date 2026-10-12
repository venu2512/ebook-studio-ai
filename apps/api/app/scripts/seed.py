"""Seed script: templates plus optional demo/admin accounts.

Usage (from ``apps/api``)::

    uv run python -m app.scripts.seed                 # templates + demo accounts
    uv run python -m app.scripts.seed --no-demo       # templates only
    uv run python -m app.scripts.seed --admin-only    # templates + admin user

* On SQLite (dev/tests) the schema is created if it is missing.
* On PostgreSQL run ``alembic upgrade head`` first.
* Demo accounts are only created when ``APP_ENV != production``.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import session_scope

log = get_logger(__name__)

DEFAULT_TEMPLATES: list[dict] = [
    {
        "name": "Classic",
        "slug": "classic",
        "kind": "interior",
        "description": "Serif body, centred headings, generous margins - timeless and readable.",
        "config": {
            "fonts": {"body": "Source Serif 4", "heading": "Inter"},
            "page_size": "a5",
            "margins": "2.2cm",
            "heading_style": "centred",
            "palette": {"primary": "#1F2937", "accent": "#B45309"},
        },
        "is_premium": False,
    },
    {
        "name": "Modern",
        "slug": "modern",
        "kind": "interior",
        "description": "Sans-serif headings, left-aligned, rules between chapters.",
        "config": {
            "fonts": {"body": "Source Serif 4", "heading": "Inter"},
            "page_size": "a5",
            "margins": "2cm",
            "heading_style": "left-aligned",
            "palette": {"primary": "#111827", "accent": "#2563EB"},
        },
        "is_premium": False,
    },
    {
        "name": "Minimal",
        "slug": "minimal",
        "kind": "interior",
        "description": "Black-and-white, small caps headings, no rules or flourishes.",
        "config": {
            "fonts": {"body": "Source Serif 4", "heading": "Inter"},
            "page_size": "a5",
            "margins": "2.4cm",
            "heading_style": "small-caps",
            "palette": {"primary": "#000000", "accent": "#000000"},
        },
        "is_premium": False,
    },
    {
        "name": "Elegant",
        "slug": "elegant",
        "kind": "interior",
        "description": "Fine serif headings, threaded footers, drop caps on chapter openers.",
        "config": {
            "fonts": {"body": "Source Serif 4", "heading": "Playfair Display"},
            "page_size": "a5",
            "margins": "2.6cm",
            "heading_style": "drop-cap",
            "palette": {"primary": "#1E293B", "accent": "#7C3AED"},
        },
        "is_premium": True,
    },
    {
        "name": "Classic Cover",
        "slug": "classic-cover",
        "kind": "cover",
        "description": "Full-bleed title with a centered accent band.",
        "config": {"layout": "centered-title", "ratio": "5:8"},
        "is_premium": False,
    },
]

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@ebookstudio.local")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo-pass-123")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ebookstudio.local")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin-pass-123")


async def seed_templates() -> int:
    from sqlalchemy import select

    from app.db.models import Template

    count = 0
    async with session_scope() as db:
        for spec in DEFAULT_TEMPLATES:
            existing = await db.scalar(select(Template).where(Template.slug == spec["slug"]))
            if existing is not None:
                continue
            db.add(Template(**spec))
            count += 1
        await db.flush()
    return count


async def seed_demo_user(email: str, password: str, *, admin: bool, full_name: str) -> None:
    from app.services import users as users_service

    async with session_scope() as db:
        user = await users_service.get_by_email(db, email)
        if user is None:
            user = await users_service.create_user(
                db, email=email, password=password, full_name=full_name
            )
            user.is_verified = True
            if admin:
                user.role = "admin"
            await db.flush()
            log.info("seed_user_created", email=email, admin=admin)
        else:
            log.info("seed_user_exists", email=email)


async def ensure_schema() -> None:
    """Create tables on SQLite when missing (dev convenience only)."""
    settings = get_settings()
    if not settings.database_url.startswith("sqlite") or settings.app_env == "production":
        return
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.db.base import Base
    from app.db.models import Book  # noqa: F401  (register models)

    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def main(include_demo: bool, admin_only: bool) -> None:
    configure_logging()
    settings = get_settings()
    await ensure_schema()

    created = await seed_templates()
    log.info("templates_seeded", created=created)

    if settings.app_env == "production":
        log.info("seed_demo_skipped_production")
        return

    if include_demo or admin_only:
        await seed_demo_user(
            ADMIN_EMAIL, ADMIN_PASSWORD, admin=True, full_name="eBook Studio Admin"
        )
    if include_demo and not admin_only:
        await seed_demo_user(DEMO_EMAIL, DEMO_PASSWORD, admin=False, full_name="Demo Author")
    if include_demo or admin_only:
        log.info(
            "demo_accounts",
            admin=ADMIN_EMAIL if (include_demo or admin_only) else None,
            demo=DEMO_EMAIL if include_demo else None,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed eBook Studio AI.")
    parser.add_argument("--no-demo", action="store_true", help="Skip demo/admin accounts.")
    parser.add_argument("--admin-only", action="store_true", help="Create only the admin account.")
    args = parser.parse_args()
    asyncio.run(main(include_demo=not args.no_demo, admin_only=args.admin_only))
