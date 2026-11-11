# TEST/back/test_alert_engine.py
from datetime import timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertOrigin, AlertRule, AlertStatus, RuleOperator, SeverityLevel
from app.services.alert_engine import (
    Signal,
    apply_signals,
    auto_resolve,
    evaluate_metric_rules,
    evaluate_risk_rules,
)
from factories import make_host, now

COOLDOWN = timedelta(minutes=15)


def signal(severity: SeverityLevel = SeverityLevel.medium, metric: str = "cpu_percent") -> Signal:
    return Signal(
        origin=AlertOrigin.rule,
        severity=severity,
        metric=metric,
        rule_id=None,
        title="CPU alta",
        evidence=[{"metric": metric, "value": 95, "detail": "95%"}],
    )


def alerts(db: Session) -> list[Alert]:
    return list(db.scalars(select(Alert).order_by(Alert.id)))


def test_dedup_increments_occurrences(db: Session) -> None:
    host, t = make_host(db), now()
    apply_signals(db, host, [signal()], t, COOLDOWN)
    apply_signals(db, host, [signal()], t + timedelta(minutes=1), COOLDOWN)
    db.commit()
    [alert] = alerts(db)
    assert alert.occurrences == 2 and alert.last_seen_at > alert.first_seen_at
    assert alert.dedup_key == f"{host.id}:rule:cpu_percent"


def test_escalates_but_never_downgrades(db: Session) -> None:
    host, t = make_host(db), now()
    apply_signals(db, host, [signal(SeverityLevel.medium)], t, COOLDOWN)
    apply_signals(db, host, [signal(SeverityLevel.critical)], t, COOLDOWN)
    apply_signals(db, host, [signal(SeverityLevel.low)], t, COOLDOWN)
    db.commit()
    assert alerts(db)[0].severity == SeverityLevel.critical


def test_cooldown_after_resolution(db: Session) -> None:
    host, t = make_host(db), now()
    [alert] = apply_signals(db, host, [signal()], t, COOLDOWN)
    alert.status, alert.resolved_at = AlertStatus.resolved, t
    db.commit()
    assert apply_signals(db, host, [signal()], t + timedelta(minutes=5), COOLDOWN) == []
    created = apply_signals(db, host, [signal()], t + timedelta(minutes=16), COOLDOWN)
    db.commit()
    assert len(created) == 1 and len(alerts(db)) == 2


def test_auto_resolve_after_clean_cycles(db: Session) -> None:
    host, t = make_host(db), now()
    apply_signals(db, host, [signal(), signal(metric="mem_percent")], t, COOLDOWN)
    apply_signals(db, host, [signal(metric="mem_percent")], t + timedelta(minutes=3), COOLDOWN)
    stale_after = timedelta(minutes=2.5)
    assert auto_resolve(db, host.id, t + timedelta(minutes=2), stale_after) == 0
    assert auto_resolve(db, host.id, t + timedelta(minutes=3), stale_after) == 1
    db.commit()
    by_metric = {a.dedup_key.split(":")[-1]: a.status for a in alerts(db)}
    assert by_metric == {"cpu_percent": AlertStatus.resolved, "mem_percent": AlertStatus.active}


def _rule(**kw) -> AlertRule:
    base = {
        "id": 1,
        "name": "CPU alta sostenida",
        "metric": "cpu_percent",
        "operator": RuleOperator.gt,
        "threshold": 90,
        "duration_minutes": 5,
        "severity": SeverityLevel.high,
        "host_id": None,
        "enabled": True,
    }
    return AlertRule(**(base | kw))


def _minute(cpu: list[float]) -> pd.DataFrame:
    idx = pd.date_range(end=pd.Timestamp(now()).floor("min"), periods=len(cpu), freq="1min")
    return pd.DataFrame({"cpu_percent": cpu, "disk_percent": 95.0, "latency_ms": 100.0}, index=idx)


def test_rule_requires_sustained_duration(db: Session) -> None:
    host, events = make_host(db), pd.DataFrame(columns=["ts", "level"])
    rule = _rule()
    short = evaluate_metric_rules([rule], host, _minute([50] * 10 + [95] * 3), events, {}, now())
    assert short == []
    [sig] = evaluate_metric_rules([rule], host, _minute([50] * 4 + [95] * 8), events, {}, now())
    assert sig.rule_id == 1 and sig.value == 95 and sig.severity == SeverityLevel.high
    assert sig.evidence[0]["detail"] == "95% durante 8 min"
    assert sig.situation == "Saturación de CPU"


def test_disk_free_events_and_host_scoped_rules(db: Session) -> None:
    host, other = make_host(db), make_host(db, "otro")
    disk = _rule(
        id=2, metric="disk_free_percent", operator=RuleOperator.lt, threshold=10, duration_minutes=0
    )
    burst = _rule(
        id=3,
        metric="events_error_count",
        operator=RuleOperator.gte,
        threshold=3,
        duration_minutes=5,
    )
    scoped = _rule(id=4, host_id=other.id, duration_minutes=0)
    t = now()
    events = pd.DataFrame(
        [
            {"ts": t - timedelta(minutes=m), "level": lv}
            for m, lv in [(1, "error"), (2, "critical"), (3, "error"), (20, "error"), (1, "info")]
        ]
    )
    sigs = evaluate_metric_rules([disk, burst, scoped], host, _minute([95] * 3), events, {}, t)
    assert {s.rule_id: s.value for s in sigs} == {2: 5.0, 3: 3.0}


def test_risk_rule_with_history(db: Session) -> None:
    host, t = make_host(db), now()
    rule = _rule(
        id=5, metric="risk_score", operator=RuleOperator.gte, threshold=0.6, duration_minutes=3
    )
    ok = [(t - timedelta(minutes=1), 0.7), (t - timedelta(minutes=2), 0.65)]
    assert len(evaluate_risk_rules([rule], host, 0.72, ok, {}, t)) == 1
    broken = [(t - timedelta(minutes=1), 0.7), (t - timedelta(minutes=2), 0.4)]
    assert evaluate_risk_rules([rule], host, 0.72, broken, {}, t) == []
    assert evaluate_risk_rules([rule], host, 0.5, ok, {}, t) == []
