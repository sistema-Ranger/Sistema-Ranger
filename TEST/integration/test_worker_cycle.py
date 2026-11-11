# TEST/integration/test_worker_cycle.py
"""Ingesta en BD → ciclo del worker → predicción + alertas + estado del host."""

from datetime import timedelta

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import (
    Alert,
    AlertOrigin,
    AlertStatus,
    EventLevel,
    HostStatus,
    Prediction,
    SeverityLevel,
)
from app.services.seed import seed_defaults
from app.worker.jobs import Analyzer
from factories import add_event, add_metrics, make_host, now


def analyzer(engine: Engine) -> Analyzer:
    return Analyzer(get_settings(), sessionmaker(bind=engine, expire_on_commit=False))


def test_cycle_creates_prediction_and_correlated_alerts(db: Session, engine: Engine) -> None:
    seed_defaults(db, get_settings())
    t = now()
    host = make_host(db, "api-01", area="pagos", last_seen_at=t)
    normal = [{"cpu_percent": 20 + i % 3, "mem_percent": 50, "latency_ms": 180} for i in range(120)]
    stress = [
        {"cpu_percent": 95, "mem_percent": 88 + i * 0.5, "latency_ms": 620} for i in range(10)
    ]
    add_metrics(db, host, normal + stress, timedelta(minutes=1), t)
    for _ in range(3):
        add_event(db, host, "HTTP 503 GET /orders upstream timeout", EventLevel.error, ts=t)

    results = analyzer(engine).run_cycle(t)
    db.expire_all()

    [pred] = db.scalars(select(Prediction)).all()
    assert pred.risk_level in (SeverityLevel.high, SeverityLevel.critical)
    assert pred.failure_probability is None and pred.anomaly_score > 0.5
    assert pred.features["cpu_percent"] == 95
    origins = {a.origin for a in db.scalars(select(Alert))}
    assert {AlertOrigin.rule, AlertOrigin.correlation} <= origins
    corr = db.scalar(select(Alert).where(Alert.origin == AlertOrigin.correlation))
    assert corr.prediction_id == pred.id and corr.evidence and corr.suggested_action
    assert any(e["metric"] == "events" for e in corr.evidence)
    db.refresh(host)
    assert host.status == HostStatus.degraded
    assert results[0].risk_level == pred.risk_level

    # Segundo ciclo: deduplicación (no se crean alertas nuevas)
    count = len(db.scalars(select(Alert)).all())
    analyzer(engine).run_cycle(t + timedelta(seconds=30))
    db.expire_all()
    assert len(db.scalars(select(Alert)).all()) == count
    assert all(a.occurrences == 2 for a in db.scalars(select(Alert)))


def test_cycle_auto_resolves_and_marks_down(db: Session, engine: Engine) -> None:
    seed_defaults(db, get_settings())
    t = now()
    host = make_host(db, "db-01", last_seen_at=t)
    add_metrics(db, host, [{"mem_percent": 90}] * 5, timedelta(minutes=1), t)
    analyzer(engine).run_cycle(t)
    db.expire_all()
    assert db.scalar(select(Alert)).status == AlertStatus.active

    later = t + timedelta(minutes=10)  # sin datos frescos ni contacto
    analyzer(engine).run_cycle(later)
    db.expire_all()
    db.refresh(host)
    assert db.scalar(select(Alert)).status == AlertStatus.resolved
    assert host.status == HostStatus.down
    assert len(db.scalars(select(Prediction)).all()) == 1


def test_area_correlation_between_hosts(db: Session, engine: Engine) -> None:
    seed_defaults(db, get_settings())
    t = now()
    for name in ("web-01", "web-02"):
        h = make_host(db, name, area="tienda", last_seen_at=t)
        add_metrics(db, h, [{"mem_percent": 92}] * 3, timedelta(minutes=1), t)
    make_host(db, "solo-01", area="otra", last_seen_at=t)
    analyzer(engine).run_cycle(t)
    area = db.scalars(select(Alert).where(Alert.dedup_key.like("%:correlation:area:tienda"))).all()
    assert len(area) == 2 and all("tienda" in a.title for a in area)


def test_failing_host_does_not_stop_cycle(db: Session, engine: Engine, monkeypatch) -> None:
    t = now()
    make_host(db, "a-01", last_seen_at=t)
    make_host(db, "b-01", last_seen_at=t)
    worker = analyzer(engine)
    original = worker.analyze_host

    def flaky(session, host, rules, when):
        if host.hostname == "a-01":
            raise RuntimeError("fallo simulado")
        return original(session, host, rules, when)

    monkeypatch.setattr(worker, "analyze_host", flaky)
    results = worker.run_cycle(t)
    assert [r.host.hostname for r in results] == ["b-01"]
