"""Authentication flows: tokens, email verification, password reset, Google OAuth."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_purpose_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
)
from app.db.models import User
from app.schemas.auth import TokenResponse
from app.services import email as email_service
from app.services import users as users_service

log = get_logger(__name__)

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def issue_tokens(user: User, *, include_refresh: bool = True) -> TokenResponse:
    """Create an access token (and optionally a refresh token)."""
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user.id, extra={"plan": user.plan, "role": user.role}),
        expires_in=settings.access_token_expire_minutes * 60,
        refresh_token=create_refresh_token(user.id) if include_refresh else None,
        csrf_token=generate_csrf_token(),
    )


# ---------------------------------------------------------------------------
# Registration / verification
# ---------------------------------------------------------------------------
async def register(
    db: AsyncSession, *, email: str, password: str, full_name: str | None
) -> tuple[User, TokenResponse]:
    settings = get_settings()
    user = await users_service.create_user(
        db,
        email=email,
        password=password,
        full_name=full_name,
        # If verification is not required, treat the account as verified.
        is_verified=not settings.require_email_verification,
    )
    if settings.require_email_verification:
        await send_verification_email(db, user)
    return user, issue_tokens(user)


async def send_verification_email(db: AsyncSession, user: User) -> None:
    token = create_purpose_token(user.id, "email_verify", minutes=60 * 24)
    subject, body = email_service.verification_email(token)
    await email_service.send_email(user.email, subject, body)


async def verify_email(db: AsyncSession, token: str) -> User:
    payload = decode_token(token, expected_type="email_verify")
    user = await users_service.require_by_id(db, uuid.UUID(payload["sub"]))
    if not user.is_verified:
        user.is_verified = True
        await db.flush()
    return user


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
async def request_password_reset(db: AsyncSession, email: str) -> None:
    """Always succeeds (no account enumeration)."""
    user = await users_service.get_by_email(db, email)
    if user is None or not user.is_active:
        log.info("password_reset_unknown_email", email=email)
        return
    token = create_purpose_token(user.id, "password_reset", minutes=60)
    subject, body = email_service.password_reset_email(token)
    await email_service.send_email(user.email, subject, body)


async def reset_password(db: AsyncSession, token: str, new_password: str) -> User:
    payload = decode_token(token, expected_type="password_reset")
    user = await users_service.require_by_id(db, uuid.UUID(payload["sub"]))
    return await users_service.set_password(db, user, new_password)


# ---------------------------------------------------------------------------
# Refresh / logout
# ---------------------------------------------------------------------------
async def refresh(db: AsyncSession, refresh_token: str) -> tuple[User, TokenResponse]:
    payload = decode_token(refresh_token, expected_type="refresh")
    user = await users_service.require_by_id(db, uuid.UUID(payload["sub"]))
    if not user.is_active:
        raise UnauthorizedError("This account is disabled.", code="account_disabled")
    return user, issue_tokens(user)


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------
async def google_login(
    db: AsyncSession, *, id_token: str | None, code: str | None
) -> tuple[User, TokenResponse]:
    """Exchange a Google credential for our own tokens.

    Accepts either a raw ``id_token`` (Google Identity Services) or an OAuth
    ``code`` (redirect flow). TODO(hardening): verify the JWT signature against
    Google's JWKS locally instead of calling the tokeninfo endpoint.
    """
    settings = get_settings()
    if not settings.google_client_id:
        raise AppError(
            "Google sign-in is not configured.", code="google_not_configured", status_code=400
        )

    claims = await _google_claims(id_token=id_token, code=code)
    email = claims.get("email")
    if not email or not claims.get("email_verified", True):
        raise UnauthorizedError("Google account has no verified email.", code="google_unverified")

    user = await users_service.get_by_email(db, email)
    if user is None:
        user = await users_service.create_user(
            db,
            email=email,
            full_name=claims.get("name"),
            google_id=claims.get("sub"),
            avatar_url=claims.get("picture"),
            is_verified=True,
        )
    else:
        if not user.google_id:
            user.google_id = claims.get("sub")
        user.last_login_at = datetime.now(UTC)
        await db.flush()
    return user, issue_tokens(user)


async def _google_claims(*, id_token: str | None, code: str | None) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as client:
        if id_token:
            response = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
        elif code:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        else:
            raise AppError("Provide either id_token or code.", code="google_missing_credential")
        if response.status_code != 200:
            raise UnauthorizedError("Google authentication failed.", code="google_failed")
        data = response.json()
        if "id_token" in data and not id_token:
            verify = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": data["id_token"]})
            if verify.status_code != 200:
                raise UnauthorizedError("Google authentication failed.", code="google_failed")
            return verify.json()
        return data
