# TEST/api/test_predictions_api.py
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ModelRegistry, SeverityLevel, UserRole
from factories import make_host, make_prediction, now

API = "/api/v1"


def test_predictions_latest_series_and_summary(
    client: TestClient, db: Session, auth_headers
) -> None:
    a, b = make_host(db, "api-01"), make_host(db, "db-01")
    make_prediction(db, a, 0.3, SeverityLevel.medium, ts=now() - timedelta(minutes=2))
    make_prediction(
        db,
        a,
        0.74,
        SeverityLevel.high,
        failure_probability=0.68,
        top_factor="mem_percent_slope_15m",
        is_anomaly=True,
    )
    make_prediction(db, b, 0.1, SeverityLevel.low)
    analyst, viewer = auth_headers(UserRole.analyst), auth_headers(UserRole.viewer)

    latest = client.get(f"{API}/predictions/latest", headers=analyst).json()
    by_host = {p["hostname"]: p for p in latest}
    assert by_host["api-01"]["risk_score"] == 0.74
    assert by_host["api-01"]["top_factor"] == "mem_percent_slope_15m"

    points = client.get(f"{API}/predictions?host_id={a.id}&from=now-1h", headers=analyst).json()
    assert [p["risk_score"] for p in points] == [0.3, 0.74]

    summary = client.get(f"{API}/predictions/summary", headers=viewer).json()
    assert summary == {
        "current_risk_level": "high",
        "risk_score": 0.74,
        "failure_probability": 0.68,
        "anomalies_today": 1,
    }
    assert client.get(f"{API}/predictions/latest", headers=viewer).status_code == 403


def test_models_active_and_activate(client: TestClient, db: Session, auth_headers) -> None:
    viewer, admin = auth_headers(UserRole.viewer), auth_headers(UserRole.admin)
    res = client.get(f"{API}/models/active", headers=viewer)
    assert res.status_code == 200 and res.json() is None

    models = [
        ModelRegistry(
            name="ranger-risk",
            version=v,
            algorithm="RF",
            horizon_minutes=30,
            trained_at=datetime.now(UTC),
            artifact_path=f"r-{v}.joblib",
            is_active=(v == "1"),
            precision=0.8,
            recall=0.85,
            f1=0.82,
        )
        for v in ("1", "2")
    ]
    db.add_all(models)
    db.commit()
    assert client.get(f"{API}/models/active", headers=viewer).json()["version"] == "1"
    assert client.post(f"{API}/models/{models[1].id}/activate", headers=viewer).status_code == 403
    activated = client.post(f"{API}/models/{models[1].id}/activate", headers=admin).json()
    assert activated["is_active"] is True
    assert client.get(f"{API}/models/active", headers=viewer).json()["version"] == "2"
    assert client.post(f"{API}/models/999/activate", headers=admin).status_code == 404
