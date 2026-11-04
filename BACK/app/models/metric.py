# BACK/app/models/metric.py
from datetime import datetime
from typing import Any

from sqlalchemy import REAL, BigInteger, ForeignKey, Index, true
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    ts: Mapped[datetime]
    cpu_percent: Mapped[float] = mapped_column(REAL)
    cpu_per_core: Mapped[list[float] | None] = mapped_column(ARRAY(REAL))
    mem_percent: Mapped[float] = mapped_column(REAL)
    mem_used_mb: Mapped[int | None]
    disk_percent: Mapped[float] = mapped_column(REAL)
    disk_partitions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    net_sent_bps: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    net_recv_bps: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    latency_ms: Mapped[float | None] = mapped_column(REAL)
    error_rate: Mapped[float | None] = mapped_column(REAL)
    is_available: Mapped[bool] = mapped_column(default=True, server_default=true())
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


Index("ix_metrics_host_ts", Metric.host_id, Metric.ts.desc())
Index("ix_metrics_ts", Metric.ts.desc())
