# BACK/app/services/hosts.py
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError, not_found
from app.models import Host, HostKind, HostStatus, Metric, Prediction
from app.schemas.host import HostCreate, HostUpdate
from app.services.pagination import paginate


def host_values(data: BaseModel, exclude_unset: bool = False) -> dict[str, Any]:
    values = data.model_dump(exclude_unset=exclude_unset)
    if values.get("ip_address") is not None:
        values["ip_address"] = str(values["ip_address"])
    return values


def get_host(db: Session, host_id: int) -> Host:
    host = db.get(Host, host_id)
    if not host:
        raise not_found("Host", "HOST_NOT_FOUND")
    return host


def get_host_by_hostname(db: Session, hostname: str) -> Host:
    host = db.scalar(select(Host).where(Host.hostname == hostname))
    if not host:
        raise AppError(404, f"Host '{hostname}' no registrado", "HOST_NOT_FOUND")
    return host


def list_hosts(
    db: Session,
    page: int,
    size: int,
    environment: str | None = None,
    area: str | None = None,
    status: HostStatus | None = None,
    kind: HostKind | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    stmt = select(Host).order_by(Host.hostname)
    if environment:
        stmt = stmt.where(Host.environment == environment)
    if area:
        stmt = stmt.where(Host.area == area)
    if status:
        stmt = stmt.where(Host.status == status)
    if kind:
        stmt = stmt.where(Host.kind == kind)
    if is_active is not None:
        stmt = stmt.where(Host.is_active == is_active)
    return paginate(db, stmt, page, size)


def host_detail(db: Session, host_id: int) -> dict[str, Any]:
    host = get_host(db, host_id)
    latest_metric = db.scalar(
        select(Metric).where(Metric.host_id == host_id).order_by(Metric.ts.desc()).limit(1)
    )
    latest_prediction = db.scalar(
        select(Prediction)
        .where(Prediction.host_id == host_id)
        .order_by(Prediction.ts.desc())
        .limit(1)
    )
    return {
        **{c.name: getattr(host, c.name) for c in Host.__table__.columns},
        "latest_metric": latest_metric,
        "latest_prediction": latest_prediction,
    }


def create_host(db: Session, data: HostCreate) -> Host:
    if db.scalar(select(Host.id).where(Host.hostname == data.hostname)):
        raise AppError(409, "Ya existe un host con ese hostname", "HOSTNAME_TAKEN")
    host = Host(**host_values(data))
    db.add(host)
    db.commit()
    db.refresh(host)
    return host


def update_host(db: Session, host_id: int, data: HostUpdate) -> Host:
    host = get_host(db, host_id)
    for field, value in host_values(data, exclude_unset=True).items():
        if value is None and field in {"kind", "environment", "is_active"}:
            continue  # columnas NOT NULL
        setattr(host, field, value)
    db.commit()
    db.refresh(host)
    return host


def deactivate_host(db: Session, host_id: int) -> Host:
    host = get_host(db, host_id)
    host.is_active = False
    db.commit()
    db.refresh(host)
    return host
