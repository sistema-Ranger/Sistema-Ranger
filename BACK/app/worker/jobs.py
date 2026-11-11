# BACK/app/worker/jobs.py
"""Ciclo de análisis (07 · §7): features → predicción → reglas/modelo → alertas → estado."""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import Float, Integer, cast, delete, func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models import (
    AlertOrigin,
    AlertRule,
    Event,
    Host,
    HostStatus,
    Metric,
    Prediction,
    SeverityLevel,
)
from app.models.enums import SEVERITY_ORDER
from app.services import alert_engine
from app.services.alert_engine import Signal
from app.services.correlation import (
    ACTIONS,
    METRIC_LABELS,
    Situation,
    detect_situation,
    top_error_evidence,
)
from app.services.risk import adjust_for_context, combine, escalate, risk_level, rule_signal
from app.services.timeutil import utcnow
from app.worker.model import ModelManager
from ml.src.features import METRIC_COLUMNS, build_features, latest_vector, resample_minutely

logger = logging.getLogger(__name__)

METRICS_LOOKBACK = timedelta(hours=24)  # base del z-score
EVENTS_LOOKBACK = timedelta(minutes=60)
FRESH_DATA = timedelta(minutes=5)
PREDICTION_RETENTION = timedelta(days=30)
SEVERITY_LABEL = {
    SeverityLevel.low: "bajo",
    SeverityLevel.medium: "medio",
    SeverityLevel.high: "alto",
    SeverityLevel.critical: "crítico",
}


@dataclass
class HostResult:
    host: Host
    signals: list[Signal] = field(default_factory=list)
    risk_level: SeverityLevel | None = None


def load_minute_metrics(db: Session, host_id: int, now: datetime) -> pd.DataFrame:
    minute = func.date_trunc("minute", Metric.ts).label("ts")
    cols = [func.avg(getattr(Metric, c)).label(c) for c in METRIC_COLUMNS]
    rows = db.execute(
        select(
            minute,
            *cols,
            func.avg(cast(Metric.is_available, Integer)).cast(Float).label("is_available"),
        )
        .where(Metric.host_id == host_id, Metric.ts > now - METRICS_LOOKBACK, Metric.ts <= now)
        .group_by(minute)
        .order_by(minute)
    ).all()
    return pd.DataFrame(rows, columns=["ts", *METRIC_COLUMNS, "is_available"])


def load_events(db: Session, host_id: int, now: datetime) -> pd.DataFrame:
    rows = db.execute(
        select(Event.ts, Event.level, Event.fingerprint, Event.message).where(
            Event.host_id == host_id, Event.ts > now - EVENTS_LOOKBACK, Event.ts <= now
        )
    ).all()
    df = pd.DataFrame(rows, columns=["ts", "level", "fingerprint", "message"])
    if not df.empty:
        df["level"] = df["level"].map(lambda lv: getattr(lv, "value", lv))
    return df


def compute_status(
    host: Host, now: datetime, settings: Settings, level: SeverityLevel | None, available: bool
) -> HostStatus:
    if host.last_seen_at is None:
        return HostStatus.unknown
    if now - host.last_seen_at > timedelta(seconds=3 * settings.collect_interval) or not available:
        return HostStatus.down
    if level in (SeverityLevel.high, SeverityLevel.critical):
        return HostStatus.degraded
    return HostStatus.up


class Analyzer:
    def __init__(
        self,
        settings: Settings | None = None,
        session_factory: Callable[[], Session] = SessionLocal,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.models = ModelManager(self.settings.model_dir)

    @property
    def interval(self) -> timedelta:
        return timedelta(seconds=self.settings.analysis_interval_seconds)

    @property
    def cooldown(self) -> timedelta:
        return timedelta(minutes=self.settings.alert_cooldown_minutes)

    def run_cycle(self, now: datetime | None = None) -> list[HostResult]:
        now = now or utcnow()
        results = []
        with self.session_factory() as db:
            self.models.refresh(db)
            rules = list(db.scalars(select(AlertRule).where(AlertRule.enabled.is_(True))))
            hosts = db.scalars(select(Host).where(Host.is_active.is_(True))).all()
            for host in hosts:
                try:
                    results.append(self.analyze_host(db, host, rules, now))
                    db.commit()
                except Exception:
                    db.rollback()
                    logger.exception("Fallo analizando %s; se continúa", host.hostname)
            try:
                self.correlate_areas(db, results, now)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Fallo en la correlación por área")
        logger.info(
            "Ciclo: %d hosts, %d con señales", len(results), sum(bool(r.signals) for r in results)
        )
        return results

    def analyze_host(
        self, db: Session, host: Host, rules: list[AlertRule], now: datetime
    ) -> HostResult:
        result = HostResult(host)
        metrics = load_minute_metrics(db, host.id, now)
        has_fresh = not metrics.empty and pd.Timestamp(metrics["ts"].iloc[-1]) >= now - FRESH_DATA
        if not has_fresh:
            # Sin datos recientes: no se predice; solo estado y autorresolución
            host.status = compute_status(host, now, self.settings, None, True)
            alert_engine.auto_resolve(db, host.id, now, self.interval * 2.5)
            return result

        events = load_events(db, host.id, now)
        end = pd.Timestamp(now)
        minute = resample_minutely(metrics, end)
        features = latest_vector(build_features(metrics, events, end))
        available = bool(metrics["is_available"].iloc[-1] >= 0.5)

        rule_signals = alert_engine.evaluate_metric_rules(
            rules, host, minute, events, features, now
        )
        output = self.models.score(features)
        risk_score = combine(
            output.failure_probability,
            output.anomaly_score,
            rule_signal(s.severity for s in rule_signals),
        )
        history = [
            (p.ts, p.risk_score, p.risk_level)
            for p in db.scalars(
                select(Prediction)
                .where(Prediction.host_id == host.id, Prediction.ts > now - timedelta(hours=1))
                .order_by(Prediction.ts.desc())
            )
        ]
        level = adjust_for_context(
            risk_level(risk_score), host.environment, [lv for _, _, lv in history]
        )
        top_factor = output.top_factor
        if rule_signals and (output.anomaly_score or 0) < 0.5:
            top_factor = max(rule_signals, key=lambda s: SEVERITY_ORDER[s.severity]).metric

        prediction = Prediction(
            host_id=host.id,
            model_id=output.model_id,
            ts=now,
            anomaly_score=output.anomaly_score,
            failure_probability=output.failure_probability,
            risk_score=risk_score,
            risk_level=level,
            is_anomaly=output.is_anomaly,
            top_factor=top_factor,
            features=features,
        )
        db.add(prediction)
        db.flush()

        risk_signals = alert_engine.evaluate_risk_rules(
            rules, host, risk_score, [(ts, s) for ts, s, _ in history], features, now
        )
        signals = rule_signals + risk_signals
        for s in signals:
            s.risk_score = risk_score
        if SEVERITY_ORDER[level] >= SEVERITY_ORDER[SeverityLevel.high] and not risk_signals:
            signals.append(self._model_signal(host, level, risk_score, top_factor, features))
        correlation = self._host_correlation(host, signals, features, events, risk_score)
        if correlation:
            signals.append(correlation)

        alert_engine.apply_signals(db, host, signals, now, self.cooldown, prediction.id)
        alert_engine.auto_resolve(db, host.id, now, self.interval * 2.5)
        host.status = compute_status(host, now, self.settings, level, available)
        result.signals, result.risk_level = signals, level
        return result

    @staticmethod
    def _model_signal(
        host: Host,
        level: SeverityLevel,
        risk_score: float,
        top_factor: str | None,
        features: dict,
    ) -> Signal:
        evidence = [
            {"metric": "risk_score", "value": risk_score, "detail": f"riesgo {risk_score:.2f}"}
        ]
        if top_factor:
            value = features.get(top_factor)
            evidence.append(
                {"metric": top_factor, "value": value, "detail": f"factor principal: {top_factor}"}
            )
        return Signal(
            origin=AlertOrigin.model,
            severity=level,
            metric="risk_score",
            value=risk_score,
            title=f"Riesgo {SEVERITY_LABEL[level]} en {host.hostname}",
            description="El modelo estima un riesgo de fallo elevado",
            situation=Situation.RISK,
            suggested_action=ACTIONS[Situation.RISK],
            evidence=evidence,
            trend="rising",
            risk_score=risk_score,
        )

    @staticmethod
    def _host_correlation(
        host: Host,
        signals: list[Signal],
        features: dict,
        events: pd.DataFrame,
        risk_score: float,
    ) -> Signal | None:
        categories = {s.category for s in signals if s.origin == AlertOrigin.rule}
        if len(categories - {"risk"}) < 2:
            return None
        messages = events["message"].tolist() if not events.empty else []
        situation = detect_situation(features, categories, messages)
        severity = max((s.severity for s in signals), key=SEVERITY_ORDER.__getitem__)
        if len(categories) >= 3:
            severity = escalate(severity)
        evidence = [e for s in signals if s.origin == AlertOrigin.rule for e in s.evidence]
        evidence += top_error_evidence(events)
        labels = ", ".join(sorted(METRIC_LABELS.get(c, c) for c in categories))
        return Signal(
            origin=AlertOrigin.correlation,
            severity=severity,
            metric="host",
            title=f"{situation} en {host.hostname}"[:160],
            description=f"Señales simultáneas: {labels}",
            situation=situation,
            suggested_action=ACTIONS[situation],
            evidence=evidence,
            trend="rising",
            risk_score=risk_score,
        )

    def correlate_areas(self, db: Session, results: list[HostResult], now: datetime) -> None:
        """Señales en ≥ 2 hosts del mismo área en el mismo ciclo → alerta de correlación."""
        by_area: dict[str, list[HostResult]] = defaultdict(list)
        for r in results:
            if r.signals and r.host.area:
                by_area[r.host.area].append(r)
        for area, group in by_area.items():
            if len(group) < 2:
                continue
            severity = max(
                (s.severity for r in group for s in r.signals), key=SEVERITY_ORDER.__getitem__
            )
            evidence = [
                {
                    "metric": "host",
                    "value": None,
                    "detail": f"{r.host.hostname}: " + ", ".join(s.title for s in r.signals[:3]),
                }
                for r in group
            ]
            for r in group:
                signal = Signal(
                    origin=AlertOrigin.correlation,
                    severity=severity,
                    metric=f"area:{area}",
                    title=f"Señales simultáneas en el área {area}"[:160],
                    description=f"{len(group)} hosts del área {area} con señales simultáneas",
                    situation=Situation.DEGRADATION,
                    suggested_action=ACTIONS[Situation.DEGRADATION],
                    evidence=evidence,
                    trend="rising",
                )
                alert_engine.apply_signals(db, r.host, [signal], now, self.cooldown)


def cleanup(session_factory: Callable[[], Session] = SessionLocal) -> int:
    """Job diario: borra predicciones con más de 30 días."""
    with session_factory() as db:
        result = db.execute(
            delete(Prediction).where(Prediction.ts < utcnow() - PREDICTION_RETENTION)
        )
        db.commit()
        logger.info("Limpieza: %d predicciones antiguas eliminadas", result.rowcount)
        return result.rowcount
