"""User profile, credits and account-deletion routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.core.security import verify_password
from app.db.models import Plan
from app.schemas.common import MessageResponse, Page
from app.schemas.user import (
    CreditsRead,
    CreditTransactionRead,
    DeleteAccountRequest,
    UserRead,
    UserUpdate,
)
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(payload: UserUpdate, user: CurrentUser, db: SessionDep) -> UserRead:
    data = payload.model_dump(exclude_unset=True)
    updated = await users_service.update_profile(db, user, **data)
    return UserRead.model_validate(updated)


@router.get("/me/credits", response_model=CreditsRead)
async def get_credits(user: CurrentUser) -> CreditsRead:
    settings = get_settings()
    return CreditsRead(
        balance=user.credits_balance,
        plan=user.plan,
        monthly_allowance=settings.plan_credits(user.plan),
        credits_per_1k_tokens=settings.credits_per_1k_tokens,
    )


@router.get("/me/credits/transactions", response_model=Page[CreditTransactionRead])
async def credit_history(
    user: CurrentUser,
    db: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[CreditTransactionRead]:
    items, total = await users_service.list_transactions(db, user.id, limit=limit, offset=offset)
    return Page.build(
        [CreditTransactionRead.model_validate(i) for i in items], total, limit, offset
    )


@router.delete("/me", response_model=MessageResponse)
async def delete_me(
    payload: DeleteAccountRequest, user: CurrentUser, db: SessionDep
) -> MessageResponse:
    """GDPR account deletion. Requires confirmation and the password (if set)."""
    if not payload.confirm:
        raise ForbiddenError("Set confirm=true to delete your account.", code="confirm_required")
    if user.password_hash and not verify_password(payload.password or "", user.password_hash):
        raise ForbiddenError("Password confirmation failed.", code="invalid_password")

    # Soft-cancel the plan and deactivate; a janitor job hard-deletes later so
    # the action is reversible during a short grace window.
    user.is_active = False
    user.plan = Plan.FREE.value
    user.email = f"deleted+{user.id}@{user.email.split('@')[-1]}"
    await db.flush()
    return MessageResponse(message="Your account has been scheduled for deletion.")


@router.get("/me/export", response_model=dict)
async def export_my_data(user: CurrentUser, db: SessionDep) -> dict:
    """GDPR data portability export. Returns all user data, books, chapters and exports."""
    return await users_service.export_user_data(db, user)
