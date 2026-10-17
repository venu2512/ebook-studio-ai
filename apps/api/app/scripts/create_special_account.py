"""Create special VIP testing and superuser admin account with unlimited access.

Usage (from apps/api):
    uv run python -m app.scripts.create_special_account
"""

from __future__ import annotations

import asyncio
import os
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Book, Plan, Template, User  # noqa: F401
from app.db.session import session_scope
from app.scripts.seed import DEFAULT_TEMPLATES

log = get_logger(__name__)

VIP_ACCOUNTS = [
    {
        "email": "vip@ebookstudio.ai",
        # Credentials are never hardcoded: the password is read from this env
        # var, or generated randomly for a new account (see _resolve_password).
        "password_env": "VIP_ACCOUNT_PASSWORD",
        "full_name": "VIP Tester (Full Access)",
        "role": "admin",
        "plan": Plan.BUSINESS.value,
        "credits": 10_000_000,
    },
    {
        "email": "admin@ebookstudio.ai",
        "password_env": "ADMIN_ACCOUNT_PASSWORD",
        "full_name": "eBook Studio Admin",
        "role": "admin",
        "plan": Plan.BUSINESS.value,
        "credits": 10_000_000,
    },
]


async def ensure_schema() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def seed_templates() -> int:
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


def _resolve_password(spec: dict) -> str:
    """Resolve an account password without hardcoding credentials.

    Uses the environment variable named by ``spec["password_env"]`` when set;
    otherwise generates a strong random password (recorded on ``spec`` so
    :func:`main` can print it once for new accounts).
    """
    env_var = spec.get("password_env", "")
    password = os.environ.get(env_var, "") if env_var else ""
    if password:
        spec["password"] = password
        spec["password_explicit"] = True
        return password
    password = spec.get("password") or secrets.token_urlsafe(18)
    spec["password"] = password
    return password


async def create_or_upgrade_vip_user(spec: dict) -> None:
    email = spec["email"].lower().strip()
    password = _resolve_password(spec)
    full_name = spec["full_name"]
    role = spec["role"]
    plan = spec["plan"]
    credits = spec["credits"]

    async with session_scope() as db:
        user = await db.scalar(select(User).where(User.email == email))
        pwd_hash = hash_password(password)

        if user is None:
            user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=pwd_hash,
                full_name=full_name,
                role=role,
                plan=plan,
                is_verified=True,
                is_active=True,
                credits_balance=credits,
                default_language="en",
                default_tone="authoritative",
                settings_json={
                    "vip_mode": True,
                    "unlimited_access": True,
                    "custom_llm_provider": "nvidia",
                    "custom_llm_base_url": "https://integrate.api.nvidia.com/v1",
                    "custom_llm_model": "meta/llama-3.3-70b-instruct",
                    # The API key is intentionally not stored here; set it in
                    # the Settings UI or via the LLM_API_KEY environment var.
                },
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(user)
            await db.flush()
            log.info("special_account_created", email=email, role=role, plan=plan, credits=credits)
            print(f"[OK] Created new special account: {email}")
        else:
            # Only reset an existing account's password when one was supplied
            # explicitly (env var), never with a freshly generated value.
            if spec.get("password_explicit"):
                user.password_hash = pwd_hash
            else:
                spec["password"] = "(unchanged)"
            user.full_name = full_name
            user.role = role
            user.plan = plan
            user.is_verified = True
            user.is_active = True
            user.credits_balance = max(user.credits_balance, credits)
            if not user.settings_json:
                user.settings_json = {}
            user.settings_json["vip_mode"] = True
            user.settings_json["unlimited_access"] = True
            await db.flush()
            log.info("special_account_updated", email=email, role=role, plan=plan, credits=credits)
            print(f"[OK] Upgraded existing account to VIP: {email}")


async def main() -> None:
    configure_logging()
    print("Initializing database schema...")
    await ensure_schema()

    seeded = await seed_templates()
    if seeded:
        print(f"Seeded {seeded} interior/cover templates.")

    for account in VIP_ACCOUNTS:
        await create_or_upgrade_vip_user(account)

    print("\n" + "=" * 60)
    print("SPECIAL TESTING ACCOUNTS READY FOR FULL APP ACCESS:")
    print("=" * 60)
    for acc in VIP_ACCOUNTS:
        print(f"Email:    {acc['email']}")
        print(f"Password: {acc['password']}")
        print(f"Role:     {acc['role']} (Admin Panel + Full System Access)")
        print(f"Plan:     {acc['plan']} (Highest Tier, No Feature Restrictions)")
        print(f"Credits:  {acc['credits']:,} (Unlimited)")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
