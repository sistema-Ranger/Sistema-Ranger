# BACK/app/services/metrics.py
import csv
import io
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Alert, Host, Metric
from app.schemas.query import Bucket, MetricName


def list_metrics(
    db: Session,
    host_id: int | None,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[Metric]:
    """Lecturas crudas en orden cronológico (las `limit` más recientes del rango)."""
    stmt = select(Metric)
    if host_id is not None:
        stmt = stmt.where(Metric.host_id == host_id)
    if start:
        stmt = stmt.where(Metric.ts >= start)
    if end:
        stmt = stmt.where(Metric.ts <= end)
    rows = db.scalars(stmt.order_by(Metric.ts.desc()).limit(limit)).all()
    return list(reversed(rows))


def latest_metrics(db: Session, host_id: int | None = None) -> list[dict[str, Any]]:
    stmt = (
        select(Metric, Host.hostname)
        .join(Host, Host.id == Metric.host_id)
        .where(Host.is_active.is_(True))
        .distinct(Metric.host_id)
        .order_by(Metric.host_id, Metric.ts.desc())
    )
    if host_id is not None:
        stmt = stmt.where(Metric.host_id == host_id)
    return [
        {**{c.name: getattr(m, c.name) for c in Metric.__table__.columns}, "hostname": hostname}
        for m, hostname in db.execute(stmt)
    ]


def aggregate(
    db: Session,
    host_id: int | None,
    metric: MetricName,
    start: datetime,
    end: datetime,
    bucket: Bucket,
) -> list[dict[str, Any]]:
    column = getattr(Metric, metric.value)
    period = func.date_trunc(bucket.value, Metric.ts).label("period")
    stmt = (
        select(
            period,
            func.avg(column).label("avg"),
            func.min(column).label("min"),
            func.max(column).label("max"),
            func.count().label("samples"),
        )
        .where(Metric.ts.between(start, end))
        .group_by(period)
        .order_by(period)
    )
    alert_period = func.date_trunc(bucket.value, Alert.first_seen_at).label("period")
    alerts_stmt = (
        select(alert_period, func.count())
        .where(Alert.first_seen_at.between(start, end))
        .group_by(alert_period)
    )
    if host_id is not None:
        stmt = stmt.where(Metric.host_id == host_id)
        alerts_stmt = alerts_stmt.where(Alert.host_id == host_id)
    alerts_by_period = dict(db.execute(alerts_stmt).all())
    return [
        {
            "period": row.period,
            "avg": round(float(row.avg), 3) if row.avg is not None else None,
            "min": float(row.min) if row.min is not None else None,
            "max": float(row.max) if row.max is not None else None,
            "samples": row.samples,
            "alerts": alerts_by_period.get(row.period, 0),
        }
        for row in db.execute(stmt)
    ]


def aggregate_csv(rows: list[dict[str, Any]], hostname: str, metric: MetricName) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["period", "host", "metric", "avg", "min", "max", "samples", "alerts"])
    for row in rows:
        writer.writerow(
            [
                row["period"].isoformat(),
                hostname,
                metric.value,
                row["avg"],
                row["min"],
                row["max"],
                row["samples"],
                row["alerts"],
            ]
        )
    return buffer.getvalue()
