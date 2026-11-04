# BACK/app/routers/events.py
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EventLevel, User
from app.schemas.common import Page
from app.schemas.query import EventRead, EventSummary
from app.security.deps import NOT_VIEWER, require_roles
from app.services import events as event_service
from app.services.events import EventFilters
from app.services.timeutil import TimeRange

router = APIRouter(prefix="/events", tags=["events"])
readers = require_roles(*NOT_VIEWER)


def event_filters(
    q: str | None = Query(None, max_length=200, description="Texto a buscar en el mensaje"),
    host_id: int | None = None,
    level: list[EventLevel] | None = Query(
        None, description="Repetible: ?level=error&level=critical"
    ),
    source: str | None = Query(None, max_length=80),
    time_range: TimeRange = Depends(),
) -> EventFilters:
    return EventFilters(q, host_id, level, source, time_range.start, time_range.end)


@router.get("", response_model=Page[EventRead], summary="Buscar eventos (paginado)")
def list_events(
    filters: EventFilters = Depends(event_filters),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(readers),
) -> dict[str, Any]:
    return event_service.list_events(db, filters, page, size)


@router.get("/summary", response_model=EventSummary, summary="Conteo por nivel")
def summary(
    filters: EventFilters = Depends(event_filters),
    db: Session = Depends(get_db),
    _: User = Depends(readers),
) -> dict[str, int]:
    return event_service.summary(db, filters)
