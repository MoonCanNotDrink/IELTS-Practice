"""Authentication API router."""

import logging
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    normalize_email,
    validate_email_address,
    validate_password_rules,
    verify_password,
)
from app.services.email_service import send_password_reset_email
from app.services.password_reset_service import (
    consume_password_reset_token,
    create_password_reset_token,
    get_valid_password_reset_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    invite_code: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetValidateRequest(BaseModel):
    token: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetValidateResponse(BaseModel):
    valid: bool


class UserProfile(BaseModel):
    username: str
    email: str | None
    email_verified: bool


class EmailUpdateRequest(BaseModel):
    email: str

@router.post("/register", response_model=Token)
@limiter.limit("5/minute")
async def register_user(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    username = user_data.username.strip()
    email = validate_email_address(user_data.email)
    validate_password_rules(user_data.password)

    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
    if user_data.invite_code != settings.INVITE_CODE:
        raise HTTPException(status_code=400, detail="Invalid invite code.")

    result = await db.execute(select(User).where(User.username == username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered.")

    email_result = await db.execute(select(User).where(User.email == email))
    if email_result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_password = get_password_hash(user_data.password)
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.username, "ver": int(new_user.token_version or 0)})
    refresh_token = create_refresh_token(data={"sub": new_user.username, "ver": int(new_user.token_version or 0)})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    username = form_data.username.strip()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, cast(str, user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "ver": int(user.token_version or 0)})
    refresh_token = create_refresh_token(data={"sub": user.username, "ver": int(user.token_version or 0)})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_access_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token_data.refresh_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        token_version = int(payload.get("ver", 0))
        if username is None or token_type != "refresh":
            raise credentials_exception
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if token_version != int(user.token_version or 0):
        raise credentials_exception

    access_token = create_access_token(data={"sub": username, "ver": int(user.token_version or 0)})
    return {
        "access_token": access_token,
        "refresh_token": token_data.refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserProfile)
@limiter.limit("30/minute")
async def get_auth_profile(request: Request, current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified_at is not None,
    }


@router.put("/email", response_model=UserProfile)
@limiter.limit("10/minute")
async def bind_email(
    request: Request,
    payload: EmailUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    email = validate_email_address(payload.email)
    existing = await db.execute(select(User).where(User.email == email, User.id != current_user.id))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    if normalize_email(current_user.email or "") != email:
        current_user.email = email
        current_user.email_verified_at = None
        db.add(current_user)
        await db.flush()

    return {
        "username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified_at is not None,
    }


@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    email = validate_email_address(payload.email)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user and user.email:
        plain_token = await create_password_reset_token(
            db,
            user,
            requested_ip=request.client.host if request.client else None,
            requested_user_agent=request.headers.get("user-agent"),
        )
        reset_url = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={plain_token}"
        try:
            send_password_reset_email(user.email, reset_url)
        except Exception:
            logger.exception("Failed to send password reset email for user_id=%s", user.id)
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/password-reset/validate", response_model=PasswordResetValidateResponse)
@limiter.limit("10/minute")
async def validate_password_reset(
    request: Request,
    payload: PasswordResetValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    reset_token = await get_valid_password_reset_token(db, payload.token)
    if reset_token is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    return {"valid": True}


@router.post("/password-reset/confirm", response_model=MessageResponse)
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    payload: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    await consume_password_reset_token(db, payload.token, payload.new_password)
    return {"message": "Password has been reset successfully."}
