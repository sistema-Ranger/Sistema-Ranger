# BACK/app/routers/reports.py
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.query import AvailabilityReport
from app.security.deps import EXPORTERS, REPORT_READERS, require_roles
from app.services import reports as report_service
from app.services.timeutil import TimeRange

router = APIRouter(prefix="/reports", tags=["reports"])
DEFAULT_SPAN = timedelta(days=7)


@router.get("/availability", response_model=AvailabilityReport, summary="Disponibilidad % y MTTR")
def availability(
    time_range: TimeRange = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*REPORT_READERS)),
) -> dict[str, Any]:
    start, end = time_range.with_defaults(DEFAULT_SPAN)
    return report_service.availability(db, start, end)


@router.get("/availability.csv", summary="Exportar disponibilidad en CSV", response_class=Response)
def availability_csv(
    time_range: TimeRange = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*EXPORTERS)),
) -> Response:
    start, end = time_range.with_defaults(DEFAULT_SPAN)
    report = report_service.availability(db, start, end)
    return Response(
        report_service.availability_csv(report),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ranger_disponibilidad.csv"'},
    )
