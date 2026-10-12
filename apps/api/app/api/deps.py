"""FastAPI dependencies: database session, current user, admin guard."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_session
from app.services import users as users_service

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


async def get_current_user(
    db: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    """Resolve the authenticated user from a Bearer token."""
    token = _extract_bearer(authorization) or access_token
    if not token:
        raise UnauthorizedError("Missing authentication token.", code="missing_token")
    payload = decode_token(token, expected_type="access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid token subject.", code="token_invalid") from exc

    user = await users_service.get_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError("Account not found.", code="user_not_found")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled.", code="account_disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise ForbiddenError("Administrator access required.", code="admin_required")
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
