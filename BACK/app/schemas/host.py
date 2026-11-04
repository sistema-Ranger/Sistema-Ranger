# BACK/app/schemas/host.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, field_validator

from app.models import HostKind, HostStatus, SeverityLevel
from app.schemas.metric import MetricRead


class HostBase(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    kind: HostKind = HostKind.server
    environment: str = Field(default="dev", max_length=40)
    area: str | None = Field(default=None, max_length=80)
    ip_address: IPvAnyAddress | None = None
    os: str | None = Field(default=None, max_length=80)
    cpu_cores: int | None = Field(default=None, ge=1, le=32767)
    mem_total_mb: int | None = Field(default=None, ge=0)


class HostCreate(HostBase):
    hostname: str = Field(min_length=1, max_length=120)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hostname": "api-01",
                "display_name": "Servidor API-01",
                "kind": "server",
                "environment": "prod",
                "area": "pagos",
            }
        }
    )


class HostUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    kind: HostKind | None = None
    environment: str | None = Field(default=None, max_length=40)
    area: str | None = Field(default=None, max_length=80)
    ip_address: IPvAnyAddress | None = None
    os: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


class HostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    display_name: str | None
    kind: HostKind
    environment: str
    area: str | None
    ip_address: str | None
    os: str | None
    cpu_cores: int | None
    mem_total_mb: int | None
    status: HostStatus
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime

    @field_validator("ip_address", mode="before")
    @classmethod
    def _ip_to_str(cls, value: Any) -> str | None:
        # psycopg devuelve INET como objeto ipaddress
        return str(value) if value is not None else None


class HostRisk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    risk_level: SeverityLevel
    risk_score: float
    failure_probability: float | None
    top_factor: str | None
    ts: datetime


class HostDetail(HostRead):
    latest_metric: MetricRead | None = None
    latest_prediction: HostRisk | None = None
