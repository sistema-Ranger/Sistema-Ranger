# BACK/app/routers/metrics.py
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Metric, User
from app.schemas.metric import MetricRead
from app.schemas.query import Bucket, MetricAggregate, MetricLatest, MetricName
from app.security.deps import EXPORTERS, NOT_VIEWER, require_roles
from app.services import metrics as metric_service
from app.services.hosts import get_host
from app.services.timeutil import TimeRange

router = APIRouter(prefix="/metrics", tags=["metrics"])
readers = require_roles(*NOT_VIEWER)
DEFAULT_AGG_SPAN = timedelta(hours=24)


@router.get("", response_model=list[MetricRead], summary="Lecturas crudas (orden cronológico)")
def list_metrics(
    host_id: int | None = None,
    time_range: TimeRange = Depends(),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    _: User = Depends(readers),
) -> list[Metric]:
    return metric_service.list_metrics(db, host_id, time_range.start, time_range.end, limit)


@router.get("/latest", response_model=list[MetricLatest], summary="Última lectura por host")
def latest(
    host_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(readers)
) -> list[dict[str, Any]]:
    return metric_service.latest_metrics(db, host_id)


@router.get(
    "/aggregate", response_model=list[MetricAggregate], summary="Agregado por minuto/hora/día"
)
def aggregate(
    metric: MetricName,
    host_id: int | None = None,
    bucket: Bucket = Bucket.hour,
    time_range: TimeRange = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(readers),
) -> list[dict[str, Any]]:
    start, end = time_range.with_defaults(DEFAULT_AGG_SPAN)
    return metric_service.aggregate(db, host_id, metric, start, end, bucket)


@router.get("/export.csv", summary="Exportar agregado en CSV (analyst+)", response_class=Response)
def export_csv(
    metric: MetricName,
    host_id: int | None = None,
    bucket: Bucket = Bucket.hour,
    time_range: TimeRange = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*EXPORTERS)),
) -> Response:
    start, end = time_range.with_defaults(DEFAULT_AGG_SPAN)
    hostname = get_host(db, host_id).hostname if host_id is not None else "todos"
    rows = metric_service.aggregate(db, host_id, metric, start, end, bucket)
    filename = f"ranger_{hostname}_{metric.value}_{bucket.value}.csv"
    return Response(
        metric_service.aggregate_csv(rows, hostname, metric),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
