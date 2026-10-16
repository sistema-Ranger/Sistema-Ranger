# BACK/app/models/host.py
from datetime import datetime

from sqlalchemy import SmallInteger, String, func, true
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import HostKind, HostStatus, pg_enum


class Host(Base):
    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(primary_key=True)
    hostname: Mapped[str] = mapped_column(String(120), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    kind: Mapped[HostKind] = mapped_column(
        pg_enum(HostKind, "host_kind"), default=HostKind.server, server_default="server"
    )
    environment: Mapped[str] = mapped_column(String(40), default="dev", server_default="dev")
    area: Mapped[str | None] = mapped_column(String(80))
    ip_address: Mapped[str | None] = mapped_column(INET)
    os: Mapped[str | None] = mapped_column(String(80))
    cpu_cores: Mapped[int | None] = mapped_column(SmallInteger)
    mem_total_mb: Mapped[int | None]
    status: Mapped[HostStatus] = mapped_column(
        pg_enum(HostStatus, "host_status"), default=HostStatus.unknown, server_default="unknown"
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    last_seen_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
