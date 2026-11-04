# BACK/app/models/incident.py
from datetime import datetime

from sqlalchemy import BigInteger, Column, ForeignKey, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.alert import Alert
from app.models.enums import IncidentStatus, SeverityLevel, pg_enum
from app.models.host import Host

incident_alerts = Table(
    "incident_alerts",
    Base.metadata,
    Column("incident_id", ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column("alert_id", BigInteger, ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True),
)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    host_id: Mapped[int | None] = mapped_column(ForeignKey("hosts.id", ondelete="SET NULL"))
    severity: Mapped[SeverityLevel] = mapped_column(pg_enum(SeverityLevel, "severity_level"))
    status: Mapped[IncidentStatus] = mapped_column(
        pg_enum(IncidentStatus, "incident_status"),
        default=IncidentStatus.open,
        server_default="open",
    )
    description: Mapped[str | None] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None]
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    host: Mapped[Host | None] = relationship()
    alerts: Mapped[list[Alert]] = relationship(secondary=incident_alerts)

    @property
    def hostname(self) -> str | None:
        return self.host.hostname if self.host else None
