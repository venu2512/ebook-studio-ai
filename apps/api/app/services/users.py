"""User service: creation, lookup, authentication and profile updates."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import hash_password, needs_rehash, verify_password
from app.db.models import CreditReason, CreditTransaction, User

log = get_logger(__name__)


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def require_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User not found.", code="user_not_found")
    return user


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str | None = None,
    full_name: str | None = None,
    google_id: str | None = None,
    is_verified: bool = False,
    avatar_url: str | None = None,
    grant_signup_credits: bool = True,
) -> User:
    """Create an account. Grants the free-plan credit allowance."""
    email = email.lower().strip()
    if await get_by_email(db, email) is not None:
        raise ConflictError("An account with that email already exists.", code="email_taken")

    settings = get_settings()
    user = User(
        email=email,
        password_hash=hash_password(password) if password else None,
        full_name=full_name,
        google_id=google_id,
        avatar_url=avatar_url,
        is_verified=is_verified,
        plan="free",
        credits_balance=0,
        default_language="en",
    )
    db.add(user)
    await db.flush()

    if grant_signup_credits:
        from app.services import credits as credits_service

        await credits_service.grant(
            db,
            user_id=user.id,
            amount=settings.free_plan_monthly_credits,
            reason=CreditReason.GRANT,
            description="Welcome credits (free plan)",
            idempotency_key=f"signup:{user.id}",
        )
    log.info("user_created", user_id=str(user.id), email=email)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials, rehashing if needed. Raises on failure."""
    user = await get_by_email(db, email)
    # Always run a hash comparison to keep timing consistent for unknown emails.
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password.", code="invalid_credentials")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled.", code="account_disabled")

    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = datetime.now(UTC)
    return user


async def update_profile(db: AsyncSession, user: User, **fields: object) -> User:
    for key, value in fields.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)
    await db.flush()
    return user


async def set_password(db: AsyncSession, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    await db.flush()
    return user


async def list_transactions(
    db: AsyncSession, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
) -> tuple[list[CreditTransaction], int]:
    from sqlalchemy import func

    total = await db.scalar(
        select(func.count())
        .select_from(CreditTransaction)
        .where(CreditTransaction.user_id == user_id)
    )
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), int(total or 0)


async def export_user_data(db: AsyncSession, user: User) -> dict[str, object]:
    """Compile all user data into a portable GDPR export dictionary."""
    from app.db.models import Book, Chapter, Export

    txs, _ = await list_transactions(db, user.id, limit=500)
    books_result = await db.execute(select(Book).where(Book.user_id == user.id))
    books = list(books_result.scalars().all())

    books_data = []
    for b in books:
        ch_result = await db.execute(
            select(Chapter).where(Chapter.book_id == b.id).order_by(Chapter.order_index)
        )
        chapters = list(ch_result.scalars().all())
        books_data.append(
            {
                "id": str(b.id),
                "title": b.title,
                "subtitle": b.subtitle,
                "topic": b.topic,
                "audience": b.audience,
                "category": b.category,
                "language": b.language,
                "tone": b.tone,
                "status": b.status,
                "target_pages": b.target_pages,
                "target_word_count": b.target_word_count,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "chapters": [
                    {
                        "id": str(c.id),
                        "order_index": c.order_index,
                        "title": c.title,
                        "summary": c.summary,
                        "word_count": c.word_count,
                        "content": c.content,
                    }
                    for c in chapters
                ],
            }
        )

    exp_result = await db.execute(select(Export).where(Export.user_id == user.id))
    exports = list(exp_result.scalars().all())

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "plan": user.plan,
            "role": user.role,
            "credits_balance": user.credits_balance,
            "default_language": user.default_language,
            "default_tone": user.default_tone,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "credit_transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "balance_after": t.balance_after,
                "reason": t.reason,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txs
        ],
        "books": books_data,
        "exports": [
            {
                "id": str(e.id),
                "book_id": str(e.book_id),
                "format": e.format,
                "template": e.template,
                "status": e.status,
                "size_bytes": e.size_bytes,
                "page_count": e.page_count,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exports
        ],
    }
