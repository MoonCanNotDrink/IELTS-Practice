"""Email delivery helpers."""

from email.message import EmailMessage
import logging
import smtplib

from app.config import settings


logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    if not settings.SMTP_HOST:
        if settings.DEBUG:
            logger.info("SMTP not configured. Password reset URL for %s: %s", to_email, reset_url)
            return
        raise RuntimeError("SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your IELTS Practice password"
    message["From"] = settings.EMAIL_FROM
    message["To"] = to_email
    message.set_content(
        "We received a request to reset your IELTS Practice password.\n\n"
        f"Open this link within {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes:\n"
        f"{reset_url}\n\n"
        "If you did not request this change, you can ignore this email."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
