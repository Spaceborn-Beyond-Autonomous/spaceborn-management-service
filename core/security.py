from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or s.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, s.JWT_SECRET, algorithm=s.JWT_ALG)

def decode_token(token: str) -> Optional[dict[str, Any]]:
    s = get_settings()
    try:
        return jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALG])
    except JWTError:
        return None
