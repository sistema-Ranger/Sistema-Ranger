# BACK/app/services/alert_engine.py
"""Motor de alertas (07 · §6): reglas → señales → alertas con dedup, cooldown,
escalado y autorresolución."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertOrigin, AlertRule, AlertStatus, Host, RuleOperator, SeverityLevel
from app.models.enums import SEVERITY_ORDER
from app.services.correlation import (
    ACTIONS,
    METRIC_CATEGORY,
    METRIC_LABELS,
    metric_evidence,
    series_slope,
    situation_for_metric,
    trend_of,
)

OPERATORS = {
    RuleOperator.gt: lambda s, t: s > t,
    RuleOperator.gte: lambda s, t: s >= t,
    RuleOperator.lt: lambda s, t: s < t,
    RuleOperator.lte: lambda s, t: s <= t,
}
OPERATOR_SYMBOL = {
    RuleOperator.gt: ">",
    RuleOperator.gte: "≥",
    RuleOperator.lt: "<",
    RuleOperator.lte: "≤",
}
EVENT_WINDOW_MIN = 5  # ventana mínima para events_error_count


@dataclass
class Signal:
    origin: AlertOrigin
    severity: SeverityLevel
    metric: str
    title: str
    rule_id: int | None = None
    value: float | None = None
    description: str | None = None
    situation: str | None = None
    suggested_action: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    trend: str | None = None
    risk_score: float | None = None

    @property
    def category(self) -> str:
        return METRIC_CATEGORY.get(self.metric, self.metric)

    def dedup_key(self, host_id: int) -> str:
        return f"{host_id}:{self.origin.value}:{self.rule_id or self.metric}"[:120]


def applicable_rules(rules: list[AlertRule], host: Host) -> list[AlertRule]:
    return [r for r in rules if r.enabled and (r.host_id is None or r.host_id == host.id)]


def _rule_series(rule: AlertRule, minute: pd.DataFrame) -> pd.Series | None:
    if rule.metric == "disk_free_percent":
        return 100 - minute["disk_percent"]
    if rule.metric in minute:
        return minute[rule.metric]
    return None


def _sustained(condition: pd.Series) -> int:
    """Minutos consecutivos (desde el final) que cumplen la condición."""
    count = 0
    for ok in reversed(condition.tolist()):
        if not ok:
            break
        count += 1
    return count


def _rule_signal(
    rule: AlertRule,
    host: Host,
    value: float,
    evidence: dict[str, Any],
    trend: str,
    features: dict[str, Any],
) -> Signal:
    situation = situation_for_metric(rule.metric, features)
    label = METRIC_LABELS.get(rule.metric, rule.metric)
    return Signal(
        origin=AlertOrigin.rule,
        severity=rule.severity,
        metric=rule.metric,
        rule_id=rule.id,
        value=value,
        title=f"{rule.name} en {host.hostname}"[:160],
        description=(
            f"{label} {OPERATOR_SYMBOL[rule.operator]} {rule.threshold:g}"
            + (f" sostenido {rule.duration_minutes} min" if rule.duration_minutes else "")
        ),
        situation=situation,
        suggested_action=ACTIONS[situation],
        evidence=[evidence],
        trend=trend,
    )


def evaluate_metric_rules(
    rules: list[AlertRule],
    host: Host,
    minute: pd.DataFrame,
    events: pd.DataFrame,
    features: dict[str, Any],
    now: datetime,
) -> list[Signal]:
    """Evalúa reglas sobre la serie por minuto (todas salvo `risk_score`)."""
    signals = []
    for rule in applicable_rules(rules, host):
        if rule.metric == "risk_score":
            continue
        compare = OPERATORS[rule.operator]
        if rule.metric == "events_error_count":
            window = max(rule.duration_minutes, EVENT_WINDOW_MIN)
            recent = (
                events[
                    events["level"].isin(["error", "critical"])
                    & (pd.to_datetime(events["ts"], utc=True) > now - timedelta(minutes=window))
                ]
                if not events.empty
                else events
            )
            value = float(len(recent))
            if not compare(value, rule.threshold):
                continue
            evidence = metric_evidence(rule.metric, value, minute, features, window_minutes=window)
            signals.append(_rule_signal(rule, host, value, evidence, "rising", features))
            continue

        series = _rule_series(rule, minute)
        if series is None:
            continue
        window = max(rule.duration_minutes, 1)
        tail = series.tail(window)
        if len(tail) < window or tail.isna().any():
            continue  # sin datos suficientes para sostener la condición
        condition = compare(series.dropna(), rule.threshold)
        if not compare(tail, rule.threshold).all():
            continue
        value = float(tail.iloc[-1])
        evidence = metric_evidence(
            rule.metric, value, minute, features, sustained_minutes=_sustained(condition)
        )
        trend = trend_of(series_slope(series))
        signals.append(_rule_signal(rule, host, value, evidence, trend, features))
    return signals


def evaluate_risk_rules(
    rules: list[AlertRule],
    host: Host,
    risk_score: float,
    risk_history: list[tuple[datetime, float]],
    features: dict[str, Any],
    now: datetime,
) -> list[Signal]:
    """Reglas sobre `risk_score`: el valor actual y las predicciones de la ventana deben cumplir."""
    signals = []
    for rule in applicable_rules(rules, host):
        if rule.metric != "risk_score":
            continue
        compare = OPERATORS[rule.operator]
        if not compare(risk_score, rule.threshold):
            continue
        if rule.duration_minutes:
            since = now - timedelta(minutes=rule.duration_minutes)
            window = [score for ts, score in risk_history if ts >= since]
            if not window or not all(compare(s, rule.threshold) for s in window):
                continue
        previous = risk_history[0][1] if risk_history else risk_score
        evidence = metric_evidence("risk_score", risk_score, pd.DataFrame(), features)
        signal = _rule_signal(
            rule, host, risk_score, evidence, trend_of(risk_score - previous, 0.02), features
        )
        signal.risk_score = risk_score
        signals.append(signal)
    return signals


def _merge(alert: Alert, signal: Signal, now: datetime, prediction_id: int | None) -> None:
    alert.last_seen_at = now
    alert.evidence = signal.evidence
    alert.trend = signal.trend
    alert.situation = signal.situation
    alert.suggested_action = signal.suggested_action
    alert.description = signal.description
    if signal.risk_score is not None:
        alert.risk_score = signal.risk_score
    if prediction_id is not None:
        alert.prediction_id = prediction_id


def apply_signals(
    db: Session,
    host: Host,
    signals: list[Signal],
    now: datetime,
    cooldown: timedelta,
    prediction_id: int | None = None,
) -> list[Alert]:
    """Crea o actualiza alertas a partir de las señales del ciclo."""
    touched = []
    for signal in signals:
        key = signal.dedup_key(host.id)
        alert = db.scalar(
            select(Alert).where(Alert.dedup_key == key, Alert.status != AlertStatus.resolved)
        )
        if alert is not None:
            alert.occurrences += 1
            if SEVERITY_ORDER[signal.severity] > SEVERITY_ORDER[alert.severity]:
                alert.severity = signal.severity  # escalado
            _merge(alert, signal, now, prediction_id)
        else:
            in_cooldown = db.scalar(
                select(Alert.id)
                .where(
                    Alert.dedup_key == key,
                    Alert.status == AlertStatus.resolved,
                    Alert.resolved_at >= now - cooldown,
                )
                .limit(1)
            )
            if in_cooldown:
                continue
            alert = Alert(
                host_id=host.id,
                rule_id=signal.rule_id,
                origin=signal.origin,
                severity=signal.severity,
                status=AlertStatus.active,
                title=signal.title,
                dedup_key=key,
                occurrences=1,
                first_seen_at=now,
                risk_score=signal.risk_score,
            )
            _merge(alert, signal, now, prediction_id)
            db.add(alert)
        touched.append(alert)
    db.flush()
    return touched


def auto_resolve(db: Session, host_id: int, now: datetime, stale_after: timedelta) -> int:
    """Resuelve las alertas cuya señal no aparece desde hace `stale_after` (3 ciclos limpios)."""
    stale = db.scalars(
        select(Alert).where(
            Alert.host_id == host_id,
            Alert.status != AlertStatus.resolved,
            Alert.last_seen_at < now - stale_after,
        )
    ).all()
    for alert in stale:
        alert.status = AlertStatus.resolved
        alert.resolved_at = now
    db.flush()
    return len(stale)
