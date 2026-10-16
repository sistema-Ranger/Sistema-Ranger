# BACK/app/models/alert.py
from datetime import datetime
from typing import Any

from sqlalchemy import REAL, BigInteger, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AlertOrigin, AlertStatus, SeverityLevel, pg_enum
from app.models.host import Host


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("alert_rules.id", ondelete="SET NULL"))
    prediction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("predictions.id", ondelete="SET NULL")
    )
    origin: Mapped[AlertOrigin] = mapped_column(pg_enum(AlertOrigin, "alert_origin"))
    severity: Mapped[SeverityLevel] = mapped_column(pg_enum(SeverityLevel, "severity_level"))
    status: Mapped[AlertStatus] = mapped_column(
        pg_enum(AlertStatus, "alert_status"), default=AlertStatus.active, server_default="active"
    )
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    situation: Mapped[str | None] = mapped_column(String(160))
    evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    trend: Mapped[str | None] = mapped_column(String(20))
    risk_score: Mapped[float | None] = mapped_column(REAL)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    dedup_key: Mapped[str] = mapped_column(String(120))
    occurrences: Mapped[int] = mapped_column(default=1, server_default="1")
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    acknowledged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    acknowledged_at: Mapped[datetime | None]
    resolved_at: Mapped[datetime | None]

    host: Mapped[Host] = relationship()

    @property
    def hostname(self) -> str:
        return self.host.hostname


Index("ix_alerts_status_sev", Alert.status, Alert.severity)
Index("ix_alerts_host_ts", Alert.host_id, Alert.first_seen_at.desc())
Index(
    "ux_alerts_active_dedup",
    Alert.dedup_key,
    unique=True,
    postgresql_where=text("status <> 'resolved'"),
)
