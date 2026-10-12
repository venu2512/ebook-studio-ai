"""Password hashing and JWT helpers.

- Passwords: Argon2id via ``argon2-cffi``.
- Tokens: short-lived access JWTs plus longer-lived refresh JWTs, each with a
  ``type`` claim so a refresh token cannot be used as an access token.
- CSRF: a double-submit token helper for cookie-authenticated flows.
"""

from __future__ import annotations

import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

TokenType = Literal["access", "refresh", "email_verify", "password_reset"]

_hasher = PasswordHasher()


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verify a password against an Argon2 hash. Never raises."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return True


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID | str, *, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    return _create_token(
        str(user_id),
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        extra,
    )


def create_refresh_token(user_id: uuid.UUID | str) -> str:
    settings = get_settings()
    return _create_token(str(user_id), "refresh", timedelta(days=settings.refresh_token_expire_days))


def create_purpose_token(user_id: uuid.UUID | str, purpose: TokenType, minutes: int = 60) -> str:
    """Short-lived token for email verification / password reset."""
    return _create_token(str(user_id), purpose, timedelta(minutes=minutes))


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises :class:`UnauthorizedError` on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired.", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Token is invalid.", code="token_invalid") from exc

    if expected_type and payload.get("type") != expected_type:
        raise UnauthorizedError("Unexpected token type.", code="token_wrong_type")
    return payload


# ---------------------------------------------------------------------------
# CSRF (double-submit cookie)
# ---------------------------------------------------------------------------
def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf_token(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)


# ---------------------------------------------------------------------------
# API keys (opaque, stored hashed)
# ---------------------------------------------------------------------------
def generate_api_key() -> tuple[str, str]:
    """Return ``(plaintext, sha256_hash)`` for a new API key."""
    import hashlib

    raw = f"esk_{secrets.token_urlsafe(32)}"
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_api_key(raw: str) -> str:
    import hashlib

    return hashlib.sha256(raw.encode()).hexdigest()
