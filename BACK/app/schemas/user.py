# BACK/app/schemas/user.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole
from app.schemas.common import Email


class UserCreate(BaseModel):
    email: Email
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.viewer

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "infra@ranger.local",
                "full_name": "Ingeniero de infraestructura",
                "password": "segura123",
                "role": "infra",
            }
        }
    )


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
