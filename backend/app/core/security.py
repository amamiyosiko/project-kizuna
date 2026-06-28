from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenKind = Literal["access", "refresh"]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(subject: str, kind: TokenKind = "access", minutes: Optional[int] = None) -> str:
    if minutes is None:
        minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES if kind == "access" else 60 * 24 * 30
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "type": kind, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return create_token(subject, "access")


def create_refresh_token(subject: str) -> str:
    return create_token(subject, "refresh")


def decode_token(token: str, expected_type: TokenKind = "access") -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    subject = payload.get("sub")
    return str(subject) if subject is not None else None
