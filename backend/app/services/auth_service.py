"""Authentication service providing JWT operations and password hashing."""

import hashlib
import jwt
import re
import secrets
from datetime import timedelta
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.models import User, utc_now

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email_address(email: str) -> str:
    normalized = normalize_email(email)
    if not normalized or len(normalized) > 255 or not EMAIL_PATTERN.match(normalized):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    return normalized


def validate_password_rules(password: str) -> None:
    password_size = len(password.encode("utf-8"))
    if password_size < 8 or password_size > 72:
        raise HTTPException(status_code=400, detail="Password must be between 8 and 72 characters.")


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        try:
            token_version = int(payload.get("ver", 0))
        except (TypeError, ValueError):
            raise credentials_exception
        if username is None or token_type != "access":
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if token_version != int(user.token_version or 0):
        raise credentials_exception

    return user

async def get_current_user_optional(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)), db: AsyncSession = Depends(get_db)) -> User | None:
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
