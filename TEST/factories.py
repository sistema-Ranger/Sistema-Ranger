# TEST/factories.py
"""Creación rápida de datos de prueba directamente en la BD."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertOrigin,
    AlertStatus,
    Event,
    EventLevel,
    Host,
    HostStatus,
    Metric,
    Prediction,
    SeverityLevel,
)
from app.services.ingest import fingerprint


def now() -> datetime:
    return datetime.now(UTC)


def make_host(db: Session, hostname: str = "api-01", **kw: Any) -> Host:
    host = Host(hostname=hostname, status=kw.pop("status", HostStatus.up), **kw)
    db.add(host)
    db.commit()
    return host


def add_metrics(
    db: Session,
    host: Host,
    values: list[dict[str, Any]],
    step: timedelta,
    end: datetime | None = None,
) -> list[Metric]:
    """Inserta lecturas espaciadas `step` terminando en `end` (por defecto ahora)."""
    end = end or now()
    rows = []
    for i, v in enumerate(values):
        base = {
            "cpu_percent": 10.0,
            "mem_percent": 20.0,
            "disk_percent": 30.0,
            "is_available": True,
        }
        rows.append(Metric(host_id=host.id, ts=end - step * (len(values) - 1 - i), **(base | v)))
    db.add_all(rows)
    db.commit()
    return rows


def add_event(
    db: Session,
    host: Host,
    message: str,
    level: EventLevel = EventLevel.info,
    source: str = "api",
    ts: datetime | None = None,
) -> Event:
    event = Event(
        host_id=host.id,
        ts=ts or now(),
        level=level,
        source=source,
        message=message,
        fingerprint=fingerprint(source, message),
    )
    db.add(event)
    db.commit()
    return event


def make_alert(
    db: Session,
    host: Host,
    severity: SeverityLevel = SeverityLevel.medium,
    status: AlertStatus = AlertStatus.active,
    origin: AlertOrigin = AlertOrigin.rule,
    key: str | None = None,
    **kw: Any,
) -> Alert:
    alert = Alert(
        host_id=host.id,
        severity=severity,
        status=status,
        origin=origin,
        title=kw.pop("title", f"Alerta {severity.value}"),
        dedup_key=key or f"{host.id}:{origin.value}:{severity.value}:{now().timestamp()}",
        **kw,
    )
    db.add(alert)
    db.commit()
    return alert


def make_prediction(db: Session, host: Host, risk_score: float, level: SeverityLevel, **kw: Any):
    pred = Prediction(
        host_id=host.id,
        risk_score=risk_score,
        risk_level=level,
        ts=kw.pop("ts", now()),
        **kw,
    )
    db.add(pred)
    db.commit()
    return pred
