"""Auth routes: register, login, refresh, logout, Google, verify, reset."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.api.deps import SessionDep, get_current_user
from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.ratelimit import rate_limit
from app.db.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services import auth as auth_service
from app.services import users as users_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"


def _set_auth_cookies(response: Response, tokens: TokenResponse) -> None:
    settings = get_settings()
    max_age = settings.refresh_token_expire_days * 24 * 3600
    if tokens.refresh_token:
        response.set_cookie(
            REFRESH_COOKIE,
            tokens.refresh_token,
            max_age=max_age,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            domain=settings.cookie_domain or None,
            path="/",
        )
    if tokens.csrf_token:
        # Readable by JS so the client can echo it in the X-CSRF-Token header.
        response.set_cookie(
            CSRF_COOKIE,
            tokens.csrf_token,
            max_age=max_age,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="lax",
            domain=settings.cookie_domain or None,
            path="/",
        )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth", 10, 60))],
)
async def register(payload: RegisterRequest, response: Response, db: SessionDep) -> UserRead:
    """Create an account and start a session."""
    user, tokens = await auth_service.register(
        db, email=payload.email, password=payload.password, full_name=payload.full_name
    )
    _set_auth_cookies(response, tokens)
    response.headers["X-Access-Token"] = tokens.access_token
    return UserRead.model_validate(user)


@router.post(
    "/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("auth", 10, 60))]
)
async def login(payload: LoginRequest, response: Response, db: SessionDep) -> TokenResponse:
    """Exchange credentials for tokens."""
    user = await users_service.authenticate(db, payload.email, payload.password)
    tokens = auth_service.issue_tokens(user)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: SessionDep,
    payload: RefreshRequest | None = None,
    refresh_cookie: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse:
    """Rotate the access token using the refresh cookie (or a body token)."""
    token = (payload.refresh_token if payload else None) or refresh_cookie
    if not token:
        raise UnauthorizedError("Missing refresh token.", code="missing_refresh_token")
    _user, tokens = await auth_service.refresh(db, token)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    """Clear the auth cookies."""
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return MessageResponse(message="Signed out.")


@router.post(
    "/google",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth", 20, 60))],
)
async def google(payload: GoogleAuthRequest, response: Response, db: SessionDep) -> TokenResponse:
    """Sign in with a Google id_token or OAuth code."""
    _user, tokens = await auth_service.google_login(
        db, id_token=payload.id_token, code=payload.code
    )
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest, db: SessionDep) -> MessageResponse:
    await auth_service.verify_email(db, payload.token)
    return MessageResponse(message="Email verified.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("auth", 5, 60))],
)
async def forgot_password(payload: ForgotPasswordRequest, db: SessionDep) -> MessageResponse:
    await auth_service.request_password_reset(db, payload.email)
    # Always the same response to avoid account enumeration.
    return MessageResponse(message="If that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: SessionDep) -> MessageResponse:
    await auth_service.reset_password(db, payload.token, payload.new_password)
    return MessageResponse(message="Password updated. You can sign in now.")


@router.get("/me", response_model=UserRead)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(user)
