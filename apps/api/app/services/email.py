"""Email delivery (console in dev, SMTP when configured)."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


async def send_email(to: str, subject: str, body: str, html: str | None = None) -> None:
    """Send an email. The console backend logs instead of sending."""
    settings = get_settings()
    if settings.email_backend == "console":
        log.info("email_console", to=to, subject=subject, body=body)
        return
    await asyncio.to_thread(_send_smtp, to, subject, body, html)


def _send_smtp(to: str, subject: str, body: str, html: str | None) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except OSError as exc:
        # Never let a mail failure break a request; log and continue.
        log.error("email_send_failed", to=to, subject=subject, error=str(exc))
        return
    log.info("email_sent", to=to, subject=subject)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
def verification_email(token: str) -> tuple[str, str]:
    settings = get_settings()
    link = f"{settings.web_base_url}/verify-email?token={token}"
    subject = "Verify your eBook Studio AI account"
    body = (
        "Welcome to eBook Studio AI.\n\n"
        f"Confirm your email address to activate your account:\n{link}\n\n"
        "If you did not create this account you can ignore this email."
    )
    return subject, body


def password_reset_email(token: str) -> tuple[str, str]:
    settings = get_settings()
    link = f"{settings.web_base_url}/reset-password?token={token}"
    subject = "Reset your eBook Studio AI password"
    body = (
        "We received a request to reset your password.\n\n"
        f"Choose a new password here (the link expires in 1 hour):\n{link}\n\n"
        "If you did not request this, no action is needed."
    )
    return subject, body


def job_complete_email(book_title: str, status: str) -> tuple[str, str]:
    settings = get_settings()
    link = f"{settings.web_base_url}/dashboard"
    subject = f"Your book '{book_title}' is ready"
    if status != "succeeded":
        subject = f"Your book '{book_title}' could not be finished"
    body = (
        f"Generation of '{book_title}' finished with status: {status}.\n\n"
        f"Open your dashboard: {link}"
    )
    return subject, body
