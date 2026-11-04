# TEST/api/test_metrics_events.py
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AlertStatus, EventLevel, SeverityLevel, UserRole
from factories import add_event, add_metrics, make_alert, make_host, now

API = "/api/v1"


def test_metrics_permissions(client: TestClient, auth_headers) -> None:
    assert client.get(f"{API}/metrics").status_code == 401
    assert client.get(f"{API}/metrics", headers=auth_headers(UserRole.viewer)).status_code == 403
    dev = auth_headers(UserRole.developer)
    assert client.get(f"{API}/metrics", headers=dev).status_code == 200
    export = f"{API}/metrics/export.csv?metric=cpu_percent"
    assert client.get(export, headers=dev).status_code == 403


def test_raw_metrics_relative_range_and_order(
    client: TestClient, db: Session, auth_headers
) -> None:
    host = make_host(db)
    add_metrics(db, host, [{"cpu_percent": float(i)} for i in range(30)], timedelta(minutes=1))
    headers = auth_headers(UserRole.infra)
    rows = client.get(
        f"{API}/metrics", params={"host_id": host.id, "from": "now-15m"}, headers=headers
    ).json()
    assert 14 <= len(rows) <= 16
    assert [r["cpu_percent"] for r in rows] == sorted(r["cpu_percent"] for r in rows)
    limited = client.get(f"{API}/metrics", params={"limit": 5}, headers=headers).json()
    assert [r["cpu_percent"] for r in limited] == [25, 26, 27, 28, 29]
    bad = client.get(f"{API}/metrics", params={"from": "ayer"}, headers=headers)
    assert bad.status_code == 422 and bad.json()["code"] == "INVALID_DATE"
    assert client.get(f"{API}/metrics?limit=6000", headers=headers).status_code == 422


def test_latest_metric_per_host(client: TestClient, db: Session, auth_headers) -> None:
    a, b = make_host(db, "a-01"), make_host(db, "b-01")
    add_metrics(db, a, [{"cpu_percent": 1}, {"cpu_percent": 2}], timedelta(minutes=1))
    add_metrics(db, b, [{"cpu_percent": 9}], timedelta(minutes=1))
    rows = client.get(f"{API}/metrics/latest", headers=auth_headers(UserRole.analyst)).json()
    assert {(r["hostname"], r["cpu_percent"]) for r in rows} == {("a-01", 2), ("b-01", 9)}


def test_aggregate_and_csv(client: TestClient, db: Session, auth_headers) -> None:
    host = make_host(db)
    end = now().replace(minute=30, second=0, microsecond=0)
    add_metrics(db, host, [{"cpu_percent": v} for v in (10, 20, 30, 40)], timedelta(minutes=5), end)
    make_alert(db, host, first_seen_at=end - timedelta(minutes=5))
    params = {
        "host_id": host.id,
        "metric": "cpu_percent",
        "bucket": "hour",
        "from": (end - timedelta(hours=1)).isoformat(),
        "to": (end + timedelta(minutes=1)).isoformat(),
    }
    headers = auth_headers(UserRole.analyst)
    rows = client.get(f"{API}/metrics/aggregate", params=params, headers=headers).json()
    assert len(rows) == 1
    assert rows[0] | {"period": None} == {
        "period": None,
        "avg": 25,
        "min": 10,
        "max": 40,
        "samples": 4,
        "alerts": 1,
    }
    csv = client.get(f"{API}/metrics/export.csv", params=params, headers=headers)
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    lines = csv.text.strip().splitlines()
    assert lines[0].startswith("period,host,metric") and ",api-01,cpu_percent,25" in lines[1]
    bad = client.get(
        f"{API}/metrics/aggregate", params=params | {"metric": "temperatura"}, headers=headers
    )
    assert bad.status_code == 422


def test_events_filters_pagination_and_summary(
    client: TestClient, db: Session, auth_headers
) -> None:
    host, other = make_host(db), make_host(db, "db-01")
    add_event(db, host, "HTTP 503 upstream timeout", EventLevel.error)
    add_event(db, host, "Connection timeout to db", EventLevel.critical, source="postgres")
    add_event(db, host, "GET /health 200", EventLevel.info)
    add_event(db, other, "disk full on /var", EventLevel.warning, source="system")
    old = add_event(db, host, "timeout antiguo", EventLevel.error, ts=now() - timedelta(days=2))
    headers = auth_headers(UserRole.developer)

    res = client.get(f"{API}/events", params={"q": "TIMEOUT"}, headers=headers).json()
    assert res["total"] == 3 and res["items"][-1]["id"] == old.id  # orden ts desc
    assert res["items"][0]["hostname"] == "api-01"

    multi = client.get(
        f"{API}/events?level=error&level=critical&from=now-1d", headers=headers
    ).json()
    assert multi["total"] == 2

    page = client.get(f"{API}/events", params={"size": 2, "page": 2}, headers=headers).json()
    assert page["total"] == 5 and len(page["items"]) == 2 and page["page"] == 2

    summary = client.get(
        f"{API}/events/summary", params={"host_id": host.id, "level": "info"}, headers=headers
    ).json()
    assert summary == {"info": 1, "warning": 0, "error": 2, "critical": 1}
    assert client.get(f"{API}/events?q=%25", headers=headers).json()["total"] == 0
    assert client.get(f"{API}/events?level=fatal", headers=headers).status_code == 422


def test_events_forbidden_for_viewer(client: TestClient, auth_headers) -> None:
    assert client.get(f"{API}/events", headers=auth_headers(UserRole.viewer)).status_code == 403


def test_aggregate_counts_only_alerts_of_host(client: TestClient, db: Session, auth_headers):
    a, b = make_host(db, "a-01"), make_host(db, "b-01")
    add_metrics(db, a, [{"cpu_percent": 5}], timedelta(minutes=1))
    make_alert(db, b, SeverityLevel.high, AlertStatus.active)
    rows = client.get(
        f"{API}/metrics/aggregate",
        params={"host_id": a.id, "metric": "cpu_percent", "bucket": "day"},
        headers=auth_headers(UserRole.admin),
    ).json()
    assert rows[0]["alerts"] == 0
