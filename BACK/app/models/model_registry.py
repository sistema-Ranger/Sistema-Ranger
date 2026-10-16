# BACK/app/models/model_registry.py
from datetime import datetime

from sqlalchemy import REAL, SmallInteger, String, UniqueConstraint, false
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(20))
    algorithm: Mapped[str] = mapped_column(String(80))
    horizon_minutes: Mapped[int] = mapped_column(SmallInteger)
    trained_at: Mapped[datetime]
    n_samples: Mapped[int | None]
    precision: Mapped[float | None] = mapped_column(REAL)
    recall: Mapped[float | None] = mapped_column(REAL)
    f1: Mapped[float | None] = mapped_column(REAL)
    roc_auc: Mapped[float | None] = mapped_column(REAL)
    feature_importance: Mapped[dict[str, float] | None] = mapped_column(JSONB)
    artifact_path: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=False, server_default=false())
