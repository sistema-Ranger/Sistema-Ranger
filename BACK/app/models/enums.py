# BACK/app/models/enums.py
import enum

from sqlalchemy import Enum


class UserRole(str, enum.Enum):
    admin = "admin"
    infra = "infra"
    developer = "developer"
    analyst = "analyst"
    viewer = "viewer"


class HostKind(str, enum.Enum):
    server = "server"
    application = "application"
    service = "service"
    database = "database"


class HostStatus(str, enum.Enum):
    up = "up"
    degraded = "degraded"
    down = "down"
    unknown = "unknown"


class EventLevel(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class SeverityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"


class AlertOrigin(str, enum.Enum):
    rule = "rule"
    model = "model"
    correlation = "correlation"


class RuleOperator(str, enum.Enum):
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"


class IncidentStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    closed = "closed"


SEVERITY_ORDER: dict[SeverityLevel, int] = {
    SeverityLevel.low: 1,
    SeverityLevel.medium: 2,
    SeverityLevel.high: 3,
    SeverityLevel.critical: 4,
}


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
