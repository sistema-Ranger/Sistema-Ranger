# BACK/app/schemas/metric.py
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_BATCH = 500  # límite de lote para /ingest/* (09 · seguridad)


def ensure_utc(value: datetime) -> datetime:
    """Fechas sin zona se interpretan como UTC (ADR-09)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class DiskPartition(BaseModel):
    mount: str = Field(max_length=255)
    percent: float = Field(ge=0, le=100)
    used_gb: float | None = Field(default=None, ge=0)
    total_gb: float | None = Field(default=None, ge=0)


class MetricReading(BaseModel):
    ts: datetime
    cpu_percent: float = Field(ge=0, le=100)
    cpu_per_core: list[float] | None = Field(default=None, max_length=1024)
    mem_percent: float = Field(ge=0, le=100)
    mem_used_mb: int | None = Field(default=None, ge=0)
    disk_percent: float = Field(ge=0, le=100)
    disk_partitions: list[DiskPartition] | None = Field(default=None, max_length=64)
    net_sent_bps: float | None = Field(default=None, ge=0)
    net_recv_bps: float | None = Field(default=None, ge=0)
    latency_ms: float | None = Field(default=None, ge=0)
    error_rate: float | None = Field(default=None, ge=0, le=100)
    is_available: bool = True
    extra: dict[str, Any] | None = None

    _utc = field_validator("ts")(ensure_utc)


class MetricsBatch(BaseModel):
    hostname: str = Field(min_length=1, max_length=120)
    readings: list[MetricReading] = Field(min_length=1, max_length=MAX_BATCH)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hostname": "api-01",
                "readings": [
                    {
                        "ts": "2026-10-15T20:00:10Z",
                        "cpu_percent": 92.1,
                        "cpu_per_core": [95.0, 88.2, 91.4, 93.8],
                        "mem_percent": 87.3,
                        "mem_used_mb": 7150,
                        "disk_percent": 64.0,
                        "disk_partitions": [
                            {"mount": "/", "percent": 64.0, "used_gb": 38.4, "total_gb": 60}
                        ],
                        "net_sent_bps": 125000.0,
                        "net_recv_bps": 480000.0,
                        "latency_ms": 620,
                        "error_rate": 4.2,
                        "is_available": True,
                    }
                ],
            }
        }
    )


class MetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host_id: int
    ts: datetime
    cpu_percent: float
    cpu_per_core: list[float] | None
    mem_percent: float
    mem_used_mb: int | None
    disk_percent: float
    disk_partitions: list[dict[str, Any]] | None
    net_sent_bps: float | None
    net_recv_bps: float | None
    latency_ms: float | None
    error_rate: float | None
    is_available: bool
    extra: dict[str, Any] | None
