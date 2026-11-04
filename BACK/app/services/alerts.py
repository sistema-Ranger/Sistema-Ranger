# BACK/app/services/alerts.py
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.errors import AppError, not_found
from app.models import Alert, AlertOrigin, AlertStatus, SeverityLevel, User
from app.services.pagination import paginate
from app.services.timeutil import utcnow


def prioritized(stmt: Select) -> Select:
    """Priorización de 07: severidad → risk_score → last_seen_at (el enum ya está ordenado)."""
    return stmt.order_by(
        Alert.severity.desc(),
        Alert.risk_score.desc().nulls_last(),
        Alert.last_seen_at.desc(),
        Alert.id.desc(),
    )


def list_alerts(
    db: Session,
    page: int,
    size: int,
    status: AlertStatus | None = None,
    severity: SeverityLevel | None = None,
    origin: AlertOrigin | None = None,
    host_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, Any]:
    stmt = select(Alert).options(joinedload(Alert.host))
    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if origin:
        stmt = stmt.where(Alert.origin == origin)
    if host_id is not None:
        stmt = stmt.where(Alert.host_id == host_id)
    if start:
        stmt = stmt.where(Alert.last_seen_at >= start)
    if end:
        stmt = stmt.where(Alert.first_seen_at <= end)
    return paginate(db, prioritized(stmt), page, size)


def summary(db: Session, host_id: int | None = None) -> dict[str, int]:
    stmt = (
        select(Alert.severity, func.count())
        .where(Alert.status == AlertStatus.active)
        .group_by(Alert.severity)
    )
    if host_id is not None:
        stmt = stmt.where(Alert.host_id == host_id)
    counts = {level.value: 0 for level in SeverityLevel}
    for severity, count in db.execute(stmt):
        counts[severity.value] = count
    return counts


def get_alert(db: Session, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id, options=[joinedload(Alert.host)])
    if not alert:
        raise not_found("Alerta", "ALERT_NOT_FOUND")
    return alert


def acknowledge(db: Session, alert_id: int, user: User) -> Alert:
    alert = get_alert(db, alert_id)
    if alert.status == AlertStatus.resolved:
        raise AppError(400, "La alerta ya está resuelta", "ALERT_ALREADY_RESOLVED")
    if alert.status == AlertStatus.active:
        alert.status = AlertStatus.acknowledged
        alert.acknowledged_by = user.id
        alert.acknowledged_at = utcnow()
        db.commit()
    return alert


def resolve(db: Session, alert_id: int, user: User) -> Alert:
    alert = get_alert(db, alert_id)
    if alert.status != AlertStatus.resolved:
        now = utcnow()
        if alert.acknowledged_by is None:
            alert.acknowledged_by, alert.acknowledged_at = user.id, now
        alert.status = AlertStatus.resolved
        alert.resolved_at = now
        db.commit()
    return alert
