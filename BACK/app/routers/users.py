# BACK/app/routers/users.py
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.security.deps import ADMIN, require_roles
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_roles(*ADMIN)


@router.get("", response_model=Page[UserRead], summary="Listar usuarios")
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, Any]:
    return user_service.list_users(db, page, size)


@router.post(
    "", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Crear usuario"
)
def create_user(
    data: UserCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)
) -> User:
    return user_service.create_user(db, data)


@router.patch("/{user_id}", response_model=UserRead, summary="Editar rol, nombre o estado")
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(admin_only),
) -> User:
    return user_service.update_user(db, user_id, data, current)


@router.delete("/{user_id}", response_model=UserRead, summary="Desactivar usuario (soft delete)")
def delete_user(
    user_id: int, db: Session = Depends(get_db), current: User = Depends(admin_only)
) -> User:
    return user_service.deactivate_user(db, user_id, current)
