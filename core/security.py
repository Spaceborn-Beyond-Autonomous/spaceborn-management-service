from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from jose import jwt, JWTError
import bcrypt  # Change this
from core.config import get_settings

def hash_password(plain: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password using bcrypt"""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or s.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, s.SECRET_KEY, algorithm=s.ALGORITHM)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    s = get_settings()
    try:
        return jwt.decode(token, s.SECRET_KEY, algorithms=[s.ALGORITHM])
    except JWTError:
        return None
