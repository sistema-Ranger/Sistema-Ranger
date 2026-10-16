# BACK/app/services/users.py
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError, not_found
from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.security.hashing import hash_password, verify_password
from app.services.pagination import paginate


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AppError(
            401,
            "Email o contraseña incorrectos",
            "INVALID_CREDENTIALS",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return user


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise not_found("Usuario", "USER_NOT_FOUND")
    return user


def list_users(db: Session, page: int, size: int) -> dict[str, Any]:
    return paginate(db, select(User).order_by(User.id), page, size)


def create_user(db: Session, data: UserCreate) -> User:
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise AppError(409, "Ya existe un usuario con ese email", "EMAIL_TAKEN")
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, current: User) -> User:
    user = get_user(db, user_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if user.id == current.id and (
        changes.get("is_active") is False or changes.get("role", user.role) != user.role
    ):
        raise AppError(400, "No puedes desactivarte ni cambiar tu propio rol", "SELF_MODIFICATION")
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: int, current: User) -> User:
    if user_id == current.id:
        raise AppError(400, "No puedes desactivarte ni cambiar tu propio rol", "SELF_MODIFICATION")
    user = get_user(db, user_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
