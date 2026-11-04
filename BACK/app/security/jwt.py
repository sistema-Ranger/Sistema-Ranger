# BACK/app/security/jwt.py
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings


def create_access_token(user_id: int, role: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(UTC) + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Devuelve el payload o None si el token es inválido o expiró."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
