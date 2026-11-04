# TEST/api/test_hosts_ingest.py
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, Host, HostStatus, Metric, UserRole

REGISTER = {
    "hostname": "api-01",
    "kind": "server",
    "environment": "dev",
    "os": "Linux 6.6",
    "cpu_cores": 4,
    "mem_total_mb": 8192,
    "ip_address": "172.18.0.5",
}


def reading(**overrides) -> dict:
    base = {
        "ts": datetime.now(UTC).isoformat(),
        "cpu_percent": 42.0,
        "cpu_per_core": [40.0, 44.0],
        "mem_percent": 60.0,
        "mem_used_mb": 4900,
        "disk_percent": 55.0,
        "disk_partitions": [{"mount": "/", "percent": 55.0, "used_gb": 33, "total_gb": 60}],
        "net_sent_bps": 1000.0,
        "net_recv_bps": 2000.0,
        "latency_ms": 120,
        "error_rate": 0.5,
        "is_available": True,
    }
    return base | overrides


# ---------- Ingesta ----------


def test_ingest_requires_api_key(client: TestClient) -> None:
    assert client.post("/api/v1/ingest/register", json=REGISTER).status_code == 401
    res = client.post("/api/v1/ingest/register", json=REGISTER, headers={"X-Collector-Key": "mala"})
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_API_KEY"


def test_register_is_upsert(client: TestClient, collector_headers, db: Session) -> None:
    first = client.post("/api/v1/ingest/register", json=REGISTER, headers=collector_headers)
    assert first.status_code == 200
    host_id = first.json()["host_id"]
    second = client.post(
        "/api/v1/ingest/register",
        json={"hostname": "api-01", "os": "Linux 6.8"},
        headers=collector_headers,
    )
    assert second.json()["host_id"] == host_id
    host = db.get(Host, host_id)
    db.refresh(host)
    assert host.os == "Linux 6.8" and host.cpu_cores == 4
    assert str(host.ip_address) == "172.18.0.5"


def test_ingest_metrics_updates_host(client: TestClient, collector_headers, db: Session) -> None:
    client.post("/api/v1/ingest/register", json=REGISTER, headers=collector_headers)
    res = client.post(
        "/api/v1/ingest/metrics",
        json={"hostname": "api-01", "readings": [reading(), reading(cpu_percent=50)]},
        headers=collector_headers,
    )
    assert res.status_code == 202
    assert res.json() == {"accepted": 2}
    host = db.scalar(select(Host).where(Host.hostname == "api-01"))
    db.refresh(host)
    assert host.status == HostStatus.up and host.last_seen_at is not None
    assert len(db.scalars(select(Metric)).all()) == 2

    client.post(
        "/api/v1/ingest/metrics",
        json={"hostname": "api-01", "readings": [reading(is_available=False)]},
        headers=collector_headers,
    )
    db.refresh(host)
    assert host.status == HostStatus.down


def test_ingest_unknown_host_404(client: TestClient, collector_headers) -> None:
    res = client.post(
        "/api/v1/ingest/metrics",
        json={"hostname": "fantasma", "readings": [reading()]},
        headers=collector_headers,
    )
    assert res.status_code == 404
    assert res.json()["code"] == "HOST_NOT_FOUND"


def test_ingest_batch_limits_and_validation_422(client: TestClient, collector_headers) -> None:
    client.post("/api/v1/ingest/register", json=REGISTER, headers=collector_headers)
    too_many = {"hostname": "api-01", "readings": [reading()] * 501}
    assert (
        client.post("/api/v1/ingest/metrics", json=too_many, headers=collector_headers).status_code
        == 422
    )
    empty = {"hostname": "api-01", "readings": []}
    assert (
        client.post("/api/v1/ingest/metrics", json=empty, headers=collector_headers).status_code
        == 422
    )
    bad = {"hostname": "api-01", "readings": [reading(cpu_percent=150)]}
    assert (
        client.post("/api/v1/ingest/metrics", json=bad, headers=collector_headers).status_code
        == 422
    )


def test_ingest_events_with_fingerprint(client: TestClient, collector_headers, db: Session) -> None:
    client.post("/api/v1/ingest/register", json=REGISTER, headers=collector_headers)
    ts = "2026-10-15T20:00:09"  # sin zona → UTC
    events = [
        {"ts": ts, "level": "error", "source": "api", "message": "HTTP 503 GET /orders/12"},
        {"ts": ts, "level": "error", "source": "api", "message": "HTTP 503 GET /orders/99"},
    ]
    res = client.post(
        "/api/v1/ingest/events",
        json={"hostname": "api-01", "events": events},
        headers=collector_headers,
    )
    assert res.status_code == 202 and res.json() == {"accepted": 2}
    stored = db.scalars(select(Event)).all()
    assert len(stored) == 2
    assert stored[0].fingerprint == stored[1].fingerprint
    assert stored[0].ts.utcoffset().total_seconds() == 0
    bad_level = [{"ts": ts, "level": "fatal", "source": "api", "message": "x"}]
    assert (
        client.post(
            "/api/v1/ingest/events",
            json={"hostname": "api-01", "events": bad_level},
            headers=collector_headers,
        ).status_code
        == 422
    )


# ---------- Hosts ----------


def test_hosts_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/hosts").status_code == 401


def test_hosts_crud_and_permissions(client: TestClient, auth_headers) -> None:
    infra, viewer, admin = (
        auth_headers(UserRole.infra),
        auth_headers(UserRole.viewer),
        auth_headers(UserRole.admin),
    )
    payload = {"hostname": "db-01", "kind": "database", "environment": "prod", "area": "pagos"}
    assert client.post("/api/v1/hosts", json=payload, headers=viewer).status_code == 403
    created = client.post("/api/v1/hosts", json=payload, headers=infra)
    assert created.status_code == 201
    host_id = created.json()["id"]
    assert created.json()["status"] == "unknown"
    assert client.post("/api/v1/hosts", json=payload, headers=infra).status_code == 409

    listed = client.get("/api/v1/hosts?environment=prod&kind=database", headers=viewer).json()
    assert listed["total"] == 1
    assert client.get("/api/v1/hosts?environment=qa", headers=viewer).json()["total"] == 0

    patched = client.patch(
        f"/api/v1/hosts/{host_id}", json={"area": "core", "ip_address": "10.0.0.9"}, headers=infra
    )
    assert patched.json()["area"] == "core" and patched.json()["ip_address"] == "10.0.0.9"

    detail = client.get(f"/api/v1/hosts/{host_id}", headers=viewer).json()
    assert detail["latest_metric"] is None and detail["latest_prediction"] is None

    assert client.delete(f"/api/v1/hosts/{host_id}", headers=infra).status_code == 403
    deleted = client.delete(f"/api/v1/hosts/{host_id}", headers=admin)
    assert deleted.json()["is_active"] is False
    assert client.get("/api/v1/hosts/999", headers=viewer).status_code == 404


def test_host_detail_includes_latest_metric(
    client: TestClient, collector_headers, auth_headers
) -> None:
    host_id = client.post(
        "/api/v1/ingest/register", json=REGISTER, headers=collector_headers
    ).json()["host_id"]
    client.post(
        "/api/v1/ingest/metrics",
        json={"hostname": "api-01", "readings": [reading(cpu_percent=77)]},
        headers=collector_headers,
    )
    detail = client.get(f"/api/v1/hosts/{host_id}", headers=auth_headers(UserRole.viewer)).json()
    assert detail["latest_metric"]["cpu_percent"] == 77
    assert detail["hostname"] == "api-01"
