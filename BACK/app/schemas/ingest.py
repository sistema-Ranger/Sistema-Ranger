# BACK/app/schemas/ingest.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import EventLevel
from app.schemas.host import HostBase
from app.schemas.metric import MAX_BATCH, ensure_utc


class IngestRegister(HostBase):
    hostname: str = Field(min_length=1, max_length=120)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hostname": "api-01",
                "kind": "server",
                "environment": "dev",
                "os": "Linux 6.6",
                "cpu_cores": 4,
                "mem_total_mb": 8192,
                "ip_address": "172.18.0.5",
            }
        }
    )


class IngestRegisterResult(BaseModel):
    host_id: int


class IngestAccepted(BaseModel):
    accepted: int


class EventIn(BaseModel):
    ts: datetime
    level: EventLevel
    source: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=10_000)
    attributes: dict[str, Any] | None = None

    _utc = field_validator("ts")(ensure_utc)


class EventsBatch(BaseModel):
    hostname: str = Field(min_length=1, max_length=120)
    events: list[EventIn] = Field(min_length=1, max_length=MAX_BATCH)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hostname": "api-01",
                "events": [
                    {
                        "ts": "2026-10-15T20:00:09Z",
                        "level": "error",
                        "source": "api",
                        "message": "HTTP 503 GET /orders upstream timeout",
                        "attributes": {"status_code": 503, "path": "/orders"},
                    }
                ],
            }
        }
    )
