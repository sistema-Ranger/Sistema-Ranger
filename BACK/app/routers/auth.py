# BACK/app/routers/auth.py
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.user import Token, UserRead
from app.security.deps import get_current_user
from app.security.jwt import create_access_token
from app.services import users as user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token, summary="Iniciar sesión (username = email)")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = user_service.authenticate(db, form.username, form.password)
    token = create_access_token(user.id, user.role.value)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead, summary="Usuario actual")
def me(user: User = Depends(get_current_user)) -> User:
    return user
