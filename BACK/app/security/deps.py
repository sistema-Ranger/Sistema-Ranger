# BACK/app/security/deps.py
"""Dependencias de autenticación (JWT) y autorización por rol (matriz de 05)."""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError
from app.models import User, UserRole
from app.security.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

ADMIN = (UserRole.admin,)
ADMIN_INFRA = (UserRole.admin, UserRole.infra)
NOT_VIEWER = (UserRole.admin, UserRole.infra, UserRole.developer, UserRole.analyst)
EXPORTERS = (UserRole.admin, UserRole.infra, UserRole.analyst)
REPORT_READERS = (UserRole.admin, UserRole.infra, UserRole.analyst, UserRole.viewer)


def _unauthorized(detail: str) -> AppError:
    return AppError(401, detail, "UNAUTHORIZED", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if not token:
        raise _unauthorized("No autenticado")
    payload = decode_access_token(token)
    if not payload or not str(payload.get("sub", "")).isdigit():
        raise _unauthorized("Token inválido o expirado")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise _unauthorized("Usuario inexistente o inactivo")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "Rol sin permiso para esta operación", "FORBIDDEN")
        return user

    return checker
