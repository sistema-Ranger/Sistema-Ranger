# BACK/app/services/reports.py
import csv
import io
from datetime import datetime
from typing import Any

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.models import Host, Incident, Metric

_DURATION_MIN = func.extract("epoch", Incident.closed_at - Incident.opened_at) / 60


def availability(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    """Disponibilidad % por host (muestras con is_available) y MTTR de incidentes cerrados."""
    avail = {
        row.host_id: row
        for row in db.execute(
            select(
                Metric.host_id,
                (100.0 * func.avg(cast(Metric.is_available, Integer))).label("pct"),
                func.count().label("samples"),
            )
            .where(Metric.ts.between(start, end))
            .group_by(Metric.host_id)
        )
    }
    closed = Incident.closed_at.between(start, end)
    mttr_by_host = {
        row.host_id: row
        for row in db.execute(
            select(Incident.host_id, func.count().label("n"), func.avg(_DURATION_MIN).label("mttr"))
            .where(closed)
            .group_by(Incident.host_id)
        )
    }
    total = db.execute(select(func.count(), func.avg(_DURATION_MIN)).where(closed)).one()

    hosts = []
    for host in db.scalars(select(Host).where(Host.is_active.is_(True)).order_by(Host.hostname)):
        a, m = avail.get(host.id), mttr_by_host.get(host.id)
        hosts.append(
            {
                "host_id": host.id,
                "hostname": host.hostname,
                "availability_pct": round(float(a.pct), 3) if a else None,
                "samples": a.samples if a else 0,
                "incidents_closed": m.n if m else 0,
                "mttr_minutes": round(float(m.mttr), 2) if m and m.mttr is not None else None,
            }
        )
    return {
        "from_": start,
        "to": end,
        "hosts": hosts,
        "incidents_closed": total[0],
        "mttr_minutes": round(float(total[1]), 2) if total[1] is not None else None,
    }


def availability_csv(report: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    columns = [
        "host_id",
        "hostname",
        "availability_pct",
        "samples",
        "incidents_closed",
        "mttr_minutes",
    ]
    writer.writerow(columns)
    for row in report["hosts"]:
        writer.writerow([row[c] for c in columns])
    return buffer.getvalue()
