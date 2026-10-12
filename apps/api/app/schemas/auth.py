"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    # The refresh token is normally delivered as an httpOnly cookie. It is also
    # returned here for API clients that cannot use cookies (e.g. mobile).
    refresh_token: str | None = None
    csrf_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class GoogleAuthRequest(BaseModel):
    """The web app swaps the Google code for tokens client-side or server-side."""

    id_token: str | None = None
    code: str | None = None


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
