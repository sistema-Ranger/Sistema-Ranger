# BACK/app/models/alert_rule.py
from datetime import datetime

from sqlalchemy import REAL, ForeignKey, SmallInteger, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import RuleOperator, SeverityLevel, pg_enum


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    metric: Mapped[str] = mapped_column(String(40))
    operator: Mapped[RuleOperator] = mapped_column(pg_enum(RuleOperator, "rule_operator"))
    threshold: Mapped[float] = mapped_column(REAL)
    duration_minutes: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    severity: Mapped[SeverityLevel] = mapped_column(pg_enum(SeverityLevel, "severity_level"))
    host_id: Mapped[int | None] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
