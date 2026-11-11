# BACK/app/services/ingest.py
import hashlib
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, Host, HostStatus, Metric
from app.schemas.ingest import EventsBatch, IngestRegister
from app.schemas.metric import MetricsBatch
from app.services.hosts import get_host_by_hostname, host_values

# Partes variables de un mensaje que no deben distinguir eventos repetidos
_VARIABLE_PARTS = [
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), "<uuid>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<ip>"),
    (re.compile(r"\b0x[0-9a-f]+\b"), "<hex>"),
    (re.compile(r"\d+(?:\.\d+)?"), "<n>"),
    (re.compile(r"\s+"), " "),
]


def normalize_message(message: str) -> str:
    text = message.lower()
    for pattern, replacement in _VARIABLE_PARTS:
        text = pattern.sub(replacement, text)
    return text.strip()


def fingerprint(source: str, message: str) -> str:
    """SHA-256 (64 hex) del origen + mensaje normalizado, para agrupar repetidos."""
    return hashlib.sha256(f"{source.lower()}|{normalize_message(message)}".encode()).hexdigest()


def register_host(db: Session, data: IngestRegister) -> Host:
    """Upsert por hostname: crea el host o actualiza los datos que reporta el recolector."""
    values = host_values(data)
    host = db.scalar(select(Host).where(Host.hostname == data.hostname))
    if host is None:
        host = Host(**values)
        db.add(host)
    else:
        sent = data.model_fields_set
        for field, value in values.items():
            if field in sent and value is not None:
                setattr(host, field, value)
        host.is_active = True
    host.last_seen_at = datetime.now(UTC)
    db.commit()
    db.refresh(host)
    return host


def ingest_metrics(db: Session, batch: MetricsBatch) -> int:
    host = get_host_by_hostname(db, batch.hostname)
    db.add_all(
        Metric(host_id=host.id, **reading.model_dump(mode="python")) for reading in batch.readings
    )
    latest = max(batch.readings, key=lambda r: r.ts)
    host.last_seen_at = datetime.now(UTC)
    if not latest.is_available:
        host.status = HostStatus.down
    elif host.status in (HostStatus.down, HostStatus.unknown):
        # 'degraded' lo decide el worker según el riesgo; aquí solo se marca vivo
        host.status = HostStatus.up
    db.commit()
    return len(batch.readings)


def ingest_events(db: Session, batch: EventsBatch) -> int:
    host = get_host_by_hostname(db, batch.hostname)
    db.add_all(
        Event(
            host_id=host.id,
            ts=event.ts,
            level=event.level,
            source=event.source,
            message=event.message,
            fingerprint=fingerprint(event.source, event.message),
            attributes=event.attributes,
        )
        for event in batch.events
    )
    host.last_seen_at = datetime.now(UTC)
    db.commit()
    return len(batch.events)
