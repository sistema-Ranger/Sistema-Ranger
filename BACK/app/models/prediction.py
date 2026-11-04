# BACK/app/models/prediction.py
from datetime import datetime
from typing import Any

from sqlalchemy import REAL, BigInteger, ForeignKey, Index, String, false, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SeverityLevel, pg_enum
from app.models.host import Host


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    model_id: Mapped[int | None] = mapped_column(ForeignKey("model_registry.id"))
    ts: Mapped[datetime] = mapped_column(server_default=func.now())
    anomaly_score: Mapped[float | None] = mapped_column(REAL)
    failure_probability: Mapped[float | None] = mapped_column(REAL)
    risk_score: Mapped[float] = mapped_column(REAL)
    risk_level: Mapped[SeverityLevel] = mapped_column(pg_enum(SeverityLevel, "severity_level"))
    is_anomaly: Mapped[bool] = mapped_column(default=False, server_default=false())
    top_factor: Mapped[str | None] = mapped_column(String(80))
    features: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    host: Mapped[Host] = relationship()

    @property
    def hostname(self) -> str:
        return self.host.hostname


Index("ix_predictions_host_ts", Prediction.host_id, Prediction.ts.desc())
