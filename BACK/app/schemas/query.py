# BACK/app/schemas/query.py
"""Schemas de lectura: métricas agregadas, eventos, alertas, reglas, incidentes, dashboard."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    AlertOrigin,
    AlertStatus,
    EventLevel,
    HostStatus,
    IncidentStatus,
    RuleOperator,
    SeverityLevel,
)
from app.schemas.metric import MetricRead


class MetricName(str, Enum):
    cpu_percent = "cpu_percent"
    mem_percent = "mem_percent"
    disk_percent = "disk_percent"
    net_sent_bps = "net_sent_bps"
    net_recv_bps = "net_recv_bps"
    latency_ms = "latency_ms"
    error_rate = "error_rate"


class Bucket(str, Enum):
    minute = "minute"
    hour = "hour"
    day = "day"


RuleMetric = Literal[
    "cpu_percent",
    "mem_percent",
    "disk_free_percent",
    "latency_ms",
    "error_rate",
    "risk_score",
    "events_error_count",
]


# ---------- Métricas ----------
class MetricLatest(MetricRead):
    hostname: str


class MetricAggregate(BaseModel):
    period: datetime
    avg: float | None
    min: float | None
    max: float | None
    samples: int
    alerts: int


# ---------- Eventos ----------
class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host_id: int
    hostname: str
    ts: datetime
    level: EventLevel
    source: str
    message: str
    fingerprint: str | None
    attributes: dict[str, Any] | None


class EventSummary(BaseModel):
    info: int = 0
    warning: int = 0
    error: int = 0
    critical: int = 0


# ---------- Reglas ----------
class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    metric: RuleMetric
    operator: RuleOperator
    threshold: float
    duration_minutes: int = Field(default=0, ge=0, le=1440)
    severity: SeverityLevel
    host_id: int | None = None
    enabled: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Latencia alta",
                "metric": "latency_ms",
                "operator": "gt",
                "threshold": 500,
                "duration_minutes": 5,
                "severity": "high",
                "host_id": None,
            }
        }
    )


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    metric: RuleMetric | None = None
    operator: RuleOperator | None = None
    threshold: float | None = None
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    severity: SeverityLevel | None = None
    host_id: int | None = None
    enabled: bool | None = None


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    metric: str
    operator: RuleOperator
    threshold: float
    duration_minutes: int
    severity: SeverityLevel
    host_id: int | None
    enabled: bool
    created_at: datetime


# ---------- Alertas ----------
class EvidenceItem(BaseModel):
    metric: str
    value: float | None = None
    detail: str


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host_id: int
    hostname: str
    rule_id: int | None
    prediction_id: int | None
    origin: AlertOrigin
    severity: SeverityLevel
    status: AlertStatus
    title: str
    description: str | None
    situation: str | None
    evidence: list[EvidenceItem] | None
    trend: str | None
    risk_score: float | None
    suggested_action: str | None
    occurrences: int
    first_seen_at: datetime
    last_seen_at: datetime
    acknowledged_by: int | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class AlertSummary(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


# ---------- Incidentes ----------
class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    host_id: int | None = None
    severity: SeverityLevel
    description: str | None = None
    assigned_to: int | None = None
    alert_ids: list[int] = Field(default_factory=list, max_length=200)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Degradación en api-01",
                "host_id": 1,
                "severity": "high",
                "description": "Latencia y errores 5xx en aumento",
                "alert_ids": [42],
            }
        }
    )


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    severity: SeverityLevel | None = None
    status: IncidentStatus | None = None
    description: str | None = None
    root_cause: str | None = None
    resolution: str | None = None
    assigned_to: int | None = None
    alert_ids: list[int] | None = Field(default=None, max_length=200)


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    host_id: int | None
    hostname: str | None
    severity: SeverityLevel
    status: IncidentStatus
    description: str | None
    root_cause: str | None
    resolution: str | None
    opened_at: datetime
    closed_at: datetime | None
    created_by: int | None
    assigned_to: int | None


class IncidentDetail(IncidentRead):
    alerts: list[AlertRead]


# ---------- Dashboard ----------
class Kpi(BaseModel):
    value: float | None
    unit: str
    trend: list[float]


class DashboardKpis(BaseModel):
    cpu: Kpi
    mem: Kpi
    disk: Kpi
    net: Kpi


class SeriesPoint(BaseModel):
    ts: datetime
    cpu: float | None
    mem: float | None
    disk: float | None
    net: float | None


class GlobalRisk(BaseModel):
    level: SeverityLevel | None
    score: float | None


class RecentAlert(BaseModel):
    id: int
    severity: SeverityLevel
    status: AlertStatus
    hostname: str
    title: str
    first_seen_at: datetime


class DashboardHost(BaseModel):
    id: int
    hostname: str
    display_name: str | None
    status: HostStatus
    last_seen_at: datetime | None
    risk_level: SeverityLevel | None


class DashboardOverview(BaseModel):
    kpis: DashboardKpis
    series: list[SeriesPoint]
    risk: GlobalRisk
    recent_alerts: list[RecentAlert]
    hosts: list[DashboardHost]


# ---------- Reportes ----------
class HostAvailability(BaseModel):
    host_id: int
    hostname: str
    availability_pct: float | None
    samples: int
    incidents_closed: int
    mttr_minutes: float | None


class AvailabilityReport(BaseModel):
    from_: datetime = Field(serialization_alias="from")
    to: datetime
    hosts: list[HostAvailability]
    incidents_closed: int
    mttr_minutes: float | None
