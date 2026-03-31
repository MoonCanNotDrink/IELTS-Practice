"""Password reset token helpers."""

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import PasswordResetToken, User, utc_now
from app.services.auth_service import (
    generate_password_reset_token,
    get_password_hash,
    hash_password_reset_token,
    validate_password_rules,
)


async def create_password_reset_token(
    db: AsyncSession,
    user: User,
    *,
    requested_ip: str | None = None,
    requested_user_agent: str | None = None,
) -> str:
    now = utc_now()
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(used_at=now)
    )

    plain_token = generate_password_reset_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token(plain_token),
        expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        requested_ip=requested_ip,
        requested_user_agent=requested_user_agent,
    )
    db.add(reset_token)
    await db.flush()
    return plain_token


async def get_valid_password_reset_token(
    db: AsyncSession,
    plain_token: str,
) -> PasswordResetToken | None:
    token_hash = hash_password_reset_token(plain_token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalars().first()
    if reset_token is None:
        return None
    now = utc_now()
    if reset_token.used_at is not None or reset_token.expires_at <= now:
        return None
    return reset_token


async def consume_password_reset_token(
    db: AsyncSession,
    plain_token: str,
    new_password: str,
) -> User:
    validate_password_rules(new_password)
    reset_token = await get_valid_password_reset_token(db, plain_token)
    if reset_token is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = await db.get(User, reset_token.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    now = utc_now()
    user.hashed_password = get_password_hash(new_password)
    user.token_version = int(user.token_version or 0) + 1
    reset_token.used_at = now

    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.id != reset_token.id,
        )
        .values(used_at=now)
    )
    await db.flush()
    return user
