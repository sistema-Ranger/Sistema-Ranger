# TEST/api/test_alerts_incidents.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AlertOrigin, AlertStatus, SeverityLevel, UserRole
from app.services.seed import DEFAULT_RULES, seed_defaults
from factories import make_alert, make_host

API = "/api/v1"


# ---------- Reglas ----------


def test_rules_crud_and_permissions(client: TestClient, db: Session, auth_headers) -> None:
    seed_defaults(db, get_settings())
    analyst, infra = auth_headers(UserRole.analyst), auth_headers(UserRole.infra)
    assert (
        client.get(f"{API}/alert-rules", headers=auth_headers(UserRole.viewer)).status_code == 403
    )
    assert len(client.get(f"{API}/alert-rules", headers=analyst).json()) == len(DEFAULT_RULES)

    rule = {
        "name": "Latencia alta",
        "metric": "latency_ms",
        "operator": "gt",
        "threshold": 500,
        "duration_minutes": 5,
        "severity": "high",
    }
    assert client.post(f"{API}/alert-rules", json=rule, headers=analyst).status_code == 403
    created = client.post(f"{API}/alert-rules", json=rule, headers=infra)
    assert created.status_code == 201 and created.json()["host_id"] is None
    rule_id = created.json()["id"]

    bad_metric = client.post(f"{API}/alert-rules", json=rule | {"metric": "x"}, headers=infra)
    assert bad_metric.status_code == 422
    bad_host = client.post(f"{API}/alert-rules", json=rule | {"host_id": 999}, headers=infra)
    assert bad_host.status_code == 400 and bad_host.json()["code"] == "INVALID_HOST"

    patched = client.patch(
        f"{API}/alert-rules/{rule_id}", json={"enabled": False, "threshold": 700}, headers=infra
    ).json()
    assert patched["enabled"] is False and patched["threshold"] == 700
    assert client.delete(f"{API}/alert-rules/{rule_id}", headers=infra).status_code == 204
    assert client.delete(f"{API}/alert-rules/{rule_id}", headers=infra).status_code == 404


# ---------- Alertas ----------


def test_alerts_list_priority_filters_and_summary(
    client: TestClient, db: Session, auth_headers
) -> None:
    host = make_host(db)
    low = make_alert(db, host, SeverityLevel.low)
    crit = make_alert(db, host, SeverityLevel.critical, origin=AlertOrigin.model)
    high_a = make_alert(db, host, SeverityLevel.high, risk_score=0.6)
    high_b = make_alert(db, host, SeverityLevel.high, risk_score=0.9)
    make_alert(db, host, SeverityLevel.high, AlertStatus.resolved)
    headers = auth_headers(UserRole.viewer)

    items = client.get(f"{API}/alerts", headers=headers).json()["items"]
    assert [a["id"] for a in items[:4]] == [crit.id, high_b.id, high_a.id, items[3]["id"]]
    assert items[-1]["id"] == low.id

    active = client.get(f"{API}/alerts?status=active", headers=headers).json()
    assert active["total"] == 4
    assert client.get(f"{API}/alerts?origin=model", headers=headers).json()["total"] == 1
    summary = client.get(f"{API}/alerts/summary", headers=headers).json()
    assert summary == {"low": 1, "medium": 0, "high": 2, "critical": 1}
    assert client.get(f"{API}/alerts?status=abierta", headers=headers).status_code == 422


def test_alert_detail_ack_and_resolve(client: TestClient, db: Session, auth_headers) -> None:
    host = make_host(db)
    evidence = [{"metric": "cpu_percent", "value": 92, "detail": "92% durante 18 min"}]
    alert = make_alert(
        db, host, SeverityLevel.high, evidence=evidence, trend="rising", suggested_action="Revisar"
    )
    viewer, infra = auth_headers(UserRole.viewer), auth_headers(UserRole.infra)

    detail = client.get(f"{API}/alerts/{alert.id}", headers=viewer).json()
    assert detail["hostname"] == "api-01" and detail["evidence"] == evidence
    assert detail["trend"] == "rising"
    assert client.get(f"{API}/alerts/999", headers=viewer).json()["code"] == "ALERT_NOT_FOUND"

    assert client.post(f"{API}/alerts/{alert.id}/acknowledge", headers=viewer).status_code == 403
    acked = client.post(f"{API}/alerts/{alert.id}/acknowledge", headers=infra).json()
    assert acked["status"] == "acknowledged" and acked["acknowledged_by"] is not None
    resolved = client.post(f"{API}/alerts/{alert.id}/resolve", headers=infra).json()
    assert resolved["status"] == "resolved" and resolved["resolved_at"] is not None
    again = client.post(f"{API}/alerts/{alert.id}/acknowledge", headers=infra)
    assert again.status_code == 400 and again.json()["code"] == "ALERT_ALREADY_RESOLVED"


# ---------- Incidentes ----------


def test_incident_lifecycle(client: TestClient, db: Session, auth_headers) -> None:
    host = make_host(db)
    a1, a2 = make_alert(db, host), make_alert(db, host, SeverityLevel.high)
    infra, viewer = auth_headers(UserRole.infra), auth_headers(UserRole.viewer)
    payload = {"title": "Degradación en api-01", "severity": "high", "alert_ids": [a1.id]}

    assert client.post(f"{API}/incidents", json=payload, headers=viewer).status_code == 403
    created = client.post(f"{API}/incidents", json=payload, headers=infra)
    assert created.status_code == 201
    inc = created.json()
    assert inc["host_id"] == host.id and inc["hostname"] == "api-01"  # deducido de las alertas
    assert [a["id"] for a in inc["alerts"]] == [a1.id] and inc["status"] == "open"

    bad = client.post(f"{API}/incidents", json=payload | {"alert_ids": [999]}, headers=infra)
    assert bad.status_code == 400 and bad.json()["code"] == "INVALID_ALERT_IDS"

    patched = client.patch(
        f"{API}/incidents/{inc['id']}",
        json={"status": "resolved", "root_cause": "Fuga de memoria", "alert_ids": [a1.id, a2.id]},
        headers=infra,
    ).json()
    assert patched["closed_at"] is not None and len(patched["alerts"]) == 2
    reopened = client.patch(
        f"{API}/incidents/{inc['id']}", json={"status": "investigating"}, headers=infra
    ).json()
    assert reopened["closed_at"] is None and reopened["root_cause"] == "Fuga de memoria"

    listed = client.get(f"{API}/incidents?status=investigating", headers=viewer).json()
    assert listed["total"] == 1
    assert client.get(f"{API}/incidents/{inc['id']}", headers=viewer).status_code == 200
    assert client.get(f"{API}/incidents/999", headers=viewer).status_code == 404
    assert client.post(f"{API}/incidents", json={"title": "x"}, headers=infra).status_code == 422
