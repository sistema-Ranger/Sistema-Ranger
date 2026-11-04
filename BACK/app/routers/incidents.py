# BACK/app/routers/incidents.py
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Incident, IncidentStatus, SeverityLevel, User
from app.schemas.common import Page
from app.schemas.query import IncidentCreate, IncidentDetail, IncidentRead, IncidentUpdate
from app.security.deps import ADMIN_INFRA, get_current_user, require_roles
from app.services import incidents as incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])
editors = require_roles(*ADMIN_INFRA)


@router.get("", response_model=Page[IncidentRead], summary="Listar incidentes")
def list_incidents(
    status: IncidentStatus | None = None,
    severity: SeverityLevel | None = None,
    host_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    return incident_service.list_incidents(db, page, size, status, severity, host_id)


@router.post(
    "",
    response_model=IncidentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Crear incidente (opcional: alert_ids)",
)
def create_incident(
    data: IncidentCreate, db: Session = Depends(get_db), user: User = Depends(editors)
) -> Incident:
    return incident_service.create_incident(db, data, user)


@router.get("/{incident_id}", response_model=IncidentDetail, summary="Detalle con alertas")
def get_incident(
    incident_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> Incident:
    return incident_service.get_incident(db, incident_id)


@router.patch("/{incident_id}", response_model=IncidentDetail, summary="Actualizar incidente")
def update_incident(
    incident_id: int,
    data: IncidentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(editors),
) -> Incident:
    return incident_service.update_incident(db, incident_id, data)
