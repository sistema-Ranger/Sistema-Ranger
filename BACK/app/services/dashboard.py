# BACK/app/services/dashboard.py
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, literal, select
from sqlalchemy.orm import Session, joinedload

from app.models import Alert, Host, Metric, Prediction
from app.services.timeutil import RANGES, utcnow

TREND_POINTS = 30
_BIN_ORIGIN = datetime(2000, 1, 1, tzinfo=UTC)
_NET_MBPS = (func.coalesce(Metric.net_sent_bps, 0) + func.coalesce(Metric.net_recv_bps, 0)) / 1e6


def _round(value: Any, digits: int = 2) -> float | None:
    return round(float(value), digits) if value is not None else None


def latest_predictions(db: Session, host_id: int | None = None) -> list[Prediction]:
    """Última predicción por host activo (DISTINCT ON)."""
    stmt = (
        select(Prediction)
        .join(Host, Host.id == Prediction.host_id)
        .where(Host.is_active.is_(True))
        .options(joinedload(Prediction.host))
        .distinct(Prediction.host_id)
        .order_by(Prediction.host_id, Prediction.ts.desc())
    )
    if host_id is not None:
        stmt = stmt.where(Prediction.host_id == host_id)
    return list(db.scalars(stmt))


def overview(db: Session, host_id: int | None, range_key: str) -> dict[str, Any]:
    span = RANGES[range_key]
    end = utcnow()
    start = end - span

    def scoped(stmt: Select) -> Select:
        stmt = stmt.where(Metric.ts >= start, Metric.ts <= end)
        return stmt.where(Metric.host_id == host_id) if host_id is not None else stmt

    averages = db.execute(
        scoped(
            select(
                func.avg(Metric.cpu_percent),
                func.avg(Metric.mem_percent),
                func.avg(Metric.disk_percent),
                func.avg(_NET_MBPS),
            )
        )
    ).one()

    bucket = func.date_bin(literal(span / TREND_POINTS), Metric.ts, literal(_BIN_ORIGIN))
    series_rows = db.execute(
        scoped(
            select(
                bucket.label("ts"),
                func.avg(Metric.cpu_percent).label("cpu"),
                func.avg(Metric.mem_percent).label("mem"),
                func.avg(Metric.disk_percent).label("disk"),
                func.avg(_NET_MBPS).label("net"),
            )
        )
        .group_by("ts")
        .order_by("ts")
    ).all()
    series = [
        {
            "ts": r.ts,
            "cpu": _round(r.cpu),
            "mem": _round(r.mem),
            "disk": _round(r.disk),
            "net": _round(r.net, 3),
        }
        for r in series_rows
    ]

    def kpi(index: int, key: str, unit: str, digits: int = 2) -> dict[str, Any]:
        return {
            "value": _round(averages[index], digits),
            "unit": unit,
            "trend": [p[key] for p in series if p[key] is not None],
        }

    predictions = latest_predictions(db, host_id)
    worst = max(predictions, key=lambda p: p.risk_score, default=None)
    risk_by_host = {p.host_id: p.risk_level for p in predictions}

    alerts_stmt = select(Alert).options(joinedload(Alert.host))
    if host_id is not None:
        alerts_stmt = alerts_stmt.where(Alert.host_id == host_id)
    recent = db.scalars(alerts_stmt.order_by(Alert.first_seen_at.desc()).limit(5)).all()

    hosts_stmt = select(Host).where(Host.is_active.is_(True)).order_by(Host.hostname)
    if host_id is not None:
        hosts_stmt = hosts_stmt.where(Host.id == host_id)

    return {
        "kpis": {
            "cpu": kpi(0, "cpu", "%"),
            "mem": kpi(1, "mem", "%"),
            "disk": kpi(2, "disk", "%"),
            "net": kpi(3, "net", "MB/s", 3),
        },
        "series": series,
        "risk": {
            "level": worst.risk_level if worst else None,
            "score": _round(worst.risk_score, 3) if worst else None,
        },
        "recent_alerts": [
            {
                "id": a.id,
                "severity": a.severity,
                "status": a.status,
                "hostname": a.hostname,
                "title": a.title,
                "first_seen_at": a.first_seen_at,
            }
            for a in recent
        ],
        "hosts": [
            {
                "id": h.id,
                "hostname": h.hostname,
                "display_name": h.display_name,
                "status": h.status,
                "last_seen_at": h.last_seen_at,
                "risk_level": risk_by_host.get(h.id),
            }
            for h in db.scalars(hosts_stmt)
        ],
    }
