# BACK/app/routers/hosts.py
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Host, HostKind, HostStatus, User
from app.schemas.common import Page
from app.schemas.host import HostCreate, HostDetail, HostRead, HostUpdate
from app.security.deps import ADMIN, ADMIN_INFRA, get_current_user, require_roles
from app.services import hosts as host_service

router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("", response_model=Page[HostRead], summary="Listar hosts")
def list_hosts(
    environment: str | None = None,
    area: str | None = None,
    status: HostStatus | None = None,
    kind: HostKind | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    return host_service.list_hosts(db, page, size, environment, area, status, kind, is_active)


@router.get("/{host_id}", response_model=HostDetail, summary="Detalle + última métrica y riesgo")
def get_host(
    host_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> dict[str, Any]:
    return host_service.host_detail(db, host_id)


@router.post(
    "",
    response_model=HostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registro manual de host",
)
def create_host(
    data: HostCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*ADMIN_INFRA)),
) -> Host:
    return host_service.create_host(db, data)


@router.patch("/{host_id}", response_model=HostRead, summary="Editar metadatos")
def update_host(
    host_id: int,
    data: HostUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*ADMIN_INFRA)),
) -> Host:
    return host_service.update_host(db, host_id, data)


@router.delete("/{host_id}", response_model=HostRead, summary="Desactivar host")
def delete_host(
    host_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(*ADMIN))
) -> Host:
    return host_service.deactivate_host(db, host_id)
