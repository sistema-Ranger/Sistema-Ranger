# BACK/app/routers/alerts.py
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertOrigin, AlertStatus, SeverityLevel, User
from app.schemas.common import Page
from app.schemas.query import AlertRead, AlertSummary
from app.security.deps import ADMIN_INFRA, get_current_user, require_roles
from app.services import alerts as alert_service
from app.services.timeutil import TimeRange

router = APIRouter(prefix="/alerts", tags=["alerts"])
responders = require_roles(*ADMIN_INFRA)


@router.get("", response_model=Page[AlertRead], summary="Listar alertas (priorizadas)")
def list_alerts(
    status: AlertStatus | None = None,
    severity: SeverityLevel | None = None,
    origin: AlertOrigin | None = None,
    host_id: int | None = None,
    time_range: TimeRange = Depends(),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    return alert_service.list_alerts(
        db, page, size, status, severity, origin, host_id, time_range.start, time_range.end
    )


@router.get("/summary", response_model=AlertSummary, summary="Alertas activas por severidad")
def summary(
    host_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, int]:
    return alert_service.summary(db, host_id)


@router.get("/{alert_id}", response_model=AlertRead, summary="Detalle con evidencia")
def get_alert(
    alert_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> Alert:
    return alert_service.get_alert(db, alert_id)


@router.post("/{alert_id}/acknowledge", response_model=AlertRead, summary="Reconocer alerta")
def acknowledge(
    alert_id: int, db: Session = Depends(get_db), user: User = Depends(responders)
) -> Alert:
    return alert_service.acknowledge(db, alert_id, user)


@router.post("/{alert_id}/resolve", response_model=AlertRead, summary="Resolver alerta")
def resolve(
    alert_id: int, db: Session = Depends(get_db), user: User = Depends(responders)
) -> Alert:
    return alert_service.resolve(db, alert_id, user)
