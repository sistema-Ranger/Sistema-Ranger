# BACK/app/services/incidents.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.errors import AppError, not_found
from app.models import Alert, Host, Incident, IncidentStatus, SeverityLevel, User
from app.schemas.query import IncidentCreate, IncidentUpdate
from app.services.pagination import paginate
from app.services.timeutil import utcnow

CLOSED_STATUSES = (IncidentStatus.resolved, IncidentStatus.closed)


def _load_alerts(db: Session, alert_ids: list[int]) -> list[Alert]:
    ids = set(alert_ids)
    alerts = list(db.scalars(select(Alert).where(Alert.id.in_(ids)))) if ids else []
    if len(alerts) != len(ids):
        missing = sorted(ids - {a.id for a in alerts})
        raise AppError(400, f"Alertas inexistentes: {missing}", "INVALID_ALERT_IDS")
    return alerts


def _check_refs(db: Session, host_id: int | None, assigned_to: int | None) -> None:
    if host_id is not None and not db.get(Host, host_id):
        raise AppError(400, "El host indicado no existe", "INVALID_HOST")
    if assigned_to is not None and not db.get(User, assigned_to):
        raise AppError(400, "El usuario asignado no existe", "INVALID_USER")


def list_incidents(
    db: Session,
    page: int,
    size: int,
    status: IncidentStatus | None = None,
    severity: SeverityLevel | None = None,
    host_id: int | None = None,
) -> dict[str, Any]:
    stmt = select(Incident).options(joinedload(Incident.host)).order_by(Incident.opened_at.desc())
    if status:
        stmt = stmt.where(Incident.status == status)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if host_id is not None:
        stmt = stmt.where(Incident.host_id == host_id)
    return paginate(db, stmt, page, size)


def get_incident(db: Session, incident_id: int) -> Incident:
    incident = db.get(
        Incident,
        incident_id,
        options=[
            joinedload(Incident.host),
            selectinload(Incident.alerts).joinedload(Alert.host),
        ],
    )
    if not incident:
        raise not_found("Incidente", "INCIDENT_NOT_FOUND")
    return incident


def create_incident(db: Session, data: IncidentCreate, user: User) -> Incident:
    _check_refs(db, data.host_id, data.assigned_to)
    alerts = _load_alerts(db, data.alert_ids)
    host_id = data.host_id
    if host_id is None and alerts and len({a.host_id for a in alerts}) == 1:
        host_id = alerts[0].host_id
    incident = Incident(
        **data.model_dump(exclude={"alert_ids", "host_id"}),
        host_id=host_id,
        created_by=user.id,
        alerts=alerts,
    )
    db.add(incident)
    db.commit()
    return get_incident(db, incident.id)


def update_incident(db: Session, incident_id: int, data: IncidentUpdate) -> Incident:
    incident = get_incident(db, incident_id)
    changes = data.model_dump(exclude_unset=True)
    _check_refs(db, None, changes.get("assigned_to"))
    if "alert_ids" in changes:
        alert_ids = changes.pop("alert_ids")
        if alert_ids is not None:
            incident.alerts = _load_alerts(db, alert_ids)
    for field, value in changes.items():
        if value is None and field in {"title", "severity", "status"}:
            continue  # NOT NULL
        setattr(incident, field, value)
    if incident.status in CLOSED_STATUSES and incident.closed_at is None:
        incident.closed_at = utcnow()
    elif incident.status not in CLOSED_STATUSES:
        incident.closed_at = None
    db.commit()
    return get_incident(db, incident_id)
