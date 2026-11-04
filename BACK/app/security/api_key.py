# BACK/app/security/api_key.py
import secrets

from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.config import get_settings
from app.errors import AppError

collector_key_header = APIKeyHeader(name="X-Collector-Key", auto_error=False)


def require_collector_key(key: str | None = Depends(collector_key_header)) -> None:
    expected = get_settings().collector_api_key
    if not key or not secrets.compare_digest(key, expected):
        raise AppError(401, "API key de recolector inválida", "INVALID_API_KEY")
