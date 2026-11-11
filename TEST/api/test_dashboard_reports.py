# TEST/api/test_dashboard_reports.py
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Incident, IncidentStatus, SeverityLevel, UserRole
from factories import add_metrics, make_alert, make_host, make_prediction, now

API = "/api/v1"


def test_dashboard_empty(client: TestClient, auth_headers) -> None:
    res = client.get(f"{API}/dashboard/overview", headers=auth_headers(UserRole.viewer))
    assert res.status_code == 200
    body = res.json()
    assert body["kpis"]["cpu"] == {"value": None, "unit": "%", "trend": []}
    assert body["risk"] == {"level": None, "score": None}
    assert body["hosts"] == [] and body["recent_alerts"] == []


def test_dashboard_overview(client: TestClient, db: Session, auth_headers) -> None:
    a, b = make_host(db, "api-01"), make_host(db, "db-01")
    add_metrics(
        db,
        a,
        [{"cpu_percent": 40, "net_sent_bps": 1e6, "net_recv_bps": 1e6}, {"cpu_percent": 60}],
        timedelta(minutes=10),
    )
    add_metrics(db, b, [{"cpu_percent": 20}], timedelta(minutes=1), now() - timedelta(hours=3))
    make_prediction(db, a, 0.74, SeverityLevel.high)
    make_prediction(db, b, 0.2, SeverityLevel.low)
    for _ in range(6):
        make_alert(db, a)
    headers = auth_headers(UserRole.viewer)

    body = client.get(f"{API}/dashboard/overview?range=1h", headers=headers).json()
    assert body["kpis"]["cpu"]["value"] == 50
    assert body["kpis"]["net"]["unit"] == "MB/s" and body["kpis"]["net"]["value"] == 1
    assert len(body["kpis"]["cpu"]["trend"]) == 2 and len(body["series"]) == 2
    assert body["risk"] == {"level": "high", "score": 0.74}
    assert len(body["recent_alerts"]) == 5
    assert {h["hostname"]: h["risk_level"] for h in body["hosts"]} == {
        "api-01": "high",
        "db-01": "low",
    }

    wide = client.get(f"{API}/dashboard/overview?range=6h&host_id={b.id}", headers=headers).json()
    assert wide["kpis"]["cpu"]["value"] == 20 and wide["recent_alerts"] == []
    assert client.get(f"{API}/dashboard/overview?range=2h", headers=headers).status_code == 422


def test_availability_report_and_csv(client: TestClient, db: Session, auth_headers) -> None:
    host = make_host(db)
    add_metrics(
        db,
        host,
        [{"is_available": True}] * 3 + [{"is_available": False}],
        timedelta(minutes=1),
    )
    opened = now() - timedelta(hours=2)
    db.add(
        Incident(
            title="Caída",
            host_id=host.id,
            severity=SeverityLevel.high,
            status=IncidentStatus.closed,
            opened_at=opened,
            closed_at=opened + timedelta(minutes=30),
        )
    )
    db.commit()

    report = client.get(f"{API}/reports/availability", headers=auth_headers(UserRole.viewer))
    assert report.status_code == 200
    body = report.json()
    assert "from" in body and body["incidents_closed"] == 1 and body["mttr_minutes"] == 30
    assert body["hosts"][0]["availability_pct"] == 75 and body["hosts"][0]["samples"] == 4

    dev = auth_headers(UserRole.developer)
    assert client.get(f"{API}/reports/availability", headers=dev).status_code == 403
    viewer_csv = client.get(
        f"{API}/reports/availability.csv", headers=auth_headers(UserRole.viewer)
    )
    assert viewer_csv.status_code == 403
    csv = client.get(f"{API}/reports/availability.csv", headers=auth_headers(UserRole.analyst))
    assert csv.status_code == 200 and "api-01,75.0,4,1,30.0" in csv.text
    bad = client.get(
        f"{API}/reports/availability?from=now-1h&to=now-2h", headers=auth_headers(UserRole.admin)
    )
    assert bad.status_code == 400 and bad.json()["code"] == "INVALID_RANGE"
