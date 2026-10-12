"""Admin routes: usage analytics, user management, job inspection, agent costs.

Every route requires an authenticated administrator (``role == "admin"``).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import case, func, or_, select

from app.api.deps import CurrentAdmin, SessionDep
from app.core.errors import NotFoundError
from app.db.models import AgentRun, Book, CreditReason, CreditTransaction, Job, User
from app.schemas.admin import (
    AdminJobRead,
    AdminUserRead,
    AdminUserUpdate,
    AgentCostRow,
    UsageSummary,
)
from app.schemas.common import Page
from app.services import credits as credits_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/usage", response_model=UsageSummary)
async def usage(_: CurrentAdmin, db: SessionDep) -> UsageSummary:
    total_users = await db.scalar(select(func.count()).select_from(User))
    total_books = await db.scalar(
        select(func.count()).select_from(Book).where(Book.deleted_at.is_(None))
    )
    total_jobs = await db.scalar(select(func.count()).select_from(Job))
    failed_jobs = await db.scalar(
        select(func.count()).select_from(Job).where(Job.status == "failed")
    )
    running_jobs = await db.scalar(
        select(func.count()).select_from(Job).where(Job.status == "running")
    )

    book_totals = await db.execute(
        select(
            func.coalesce(func.sum(Book.tokens_used), 0),
            func.coalesce(func.sum(Book.cost_usd), 0.0),
        )
    )
    tokens_row = book_totals.one()

    credits_consumed = await db.scalar(
        select(func.coalesce(func.sum(-CreditTransaction.amount), 0)).where(
            CreditTransaction.reason == CreditReason.GENERATION.value
        )
    )

    return UsageSummary(
        total_users=int(total_users or 0),
        total_books=int(total_books or 0),
        total_jobs=int(total_jobs or 0),
        failed_jobs=int(failed_jobs or 0),
        running_jobs=int(running_jobs or 0),
        total_tokens=int(tokens_row[0] or 0),
        total_cost_usd=round(float(tokens_row[1] or 0.0), 6),
        credits_consumed=int(credits_consumed or 0),
    )


@router.get("/agents/costs", response_model=list[AgentCostRow])
async def agent_costs(_: CurrentAdmin, db: SessionDep) -> list[AgentCostRow]:
    result = await db.execute(
        select(
            AgentRun.agent_name,
            func.count(AgentRun.id),
            func.coalesce(func.sum(AgentRun.total_tokens), 0),
            func.coalesce(func.sum(AgentRun.cost_usd), 0.0),
            func.coalesce(func.sum(case((AgentRun.status == "failed", 1), else_=0)), 0),
        ).group_by(AgentRun.agent_name)
    )
    rows = [
        AgentCostRow(
            agent_name=row[0],
            runs=int(row[1] or 0),
            tokens=int(row[2] or 0),
            cost_usd=round(float(row[3] or 0.0), 6),
            failures=int(row[4] or 0),
        )
        for row in result.all()
    ]
    return sorted(rows, key=lambda r: r.cost_usd, reverse=True)


@router.get("/users", response_model=Page[AdminUserRead])
async def list_users(
    _: CurrentAdmin,
    db: SessionDep,
    search: str | None = Query(default=None),
    plan: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[AdminUserRead]:
    conditions = []
    if search:
        like = f"%{search.lower()}%"
        conditions.append(
            or_(
                func.lower(User.email).like(like),
                func.lower(func.coalesce(User.full_name, "")).like(like),
            )
        )
    if plan:
        conditions.append(User.plan == plan)

    total = await db.scalar(select(func.count()).select_from(User).where(*conditions))
    result = await db.execute(
        select(User).where(*conditions).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    items = [AdminUserRead.model_validate(u) for u in result.scalars().all()]
    return Page.build(items, int(total or 0), limit, offset)


@router.patch("/users/{user_id}", response_model=AdminUserRead)
async def update_user(
    user_id: uuid.UUID, payload: AdminUserUpdate, _: CurrentAdmin, db: SessionDep
) -> AdminUserRead:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.", code="user_not_found")

    for field in ("full_name", "role", "plan", "is_active", "is_verified"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)

    if payload.credits_delta:
        description = payload.credits_note or "Manual adjustment by an administrator"
        if payload.credits_delta > 0:
            await credits_service.grant(
                db,
                user_id=user.id,
                amount=payload.credits_delta,
                reason=CreditReason.ADJUSTMENT,
                description=description,
            )
        else:
            await credits_service.spend(
                db,
                user_id=user.id,
                amount=-payload.credits_delta,
                reason=CreditReason.ADJUSTMENT,
                description=description,
            )

    await db.flush()
    return AdminUserRead.model_validate(user)


@router.get("/jobs", response_model=Page[AdminJobRead])
async def list_jobs(
    _: CurrentAdmin,
    db: SessionDep,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[AdminJobRead]:
    conditions = []
    if status_filter:
        conditions.append(Job.status == status_filter)
    total = await db.scalar(select(func.count()).select_from(Job).where(*conditions))
    result = await db.execute(
        select(Job).where(*conditions).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    )
    items = [AdminJobRead.model_validate(j) for j in result.scalars().all()]
    return Page.build(items, int(total or 0), limit, offset)
