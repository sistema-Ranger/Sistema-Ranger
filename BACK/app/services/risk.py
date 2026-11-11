# BACK/app/services/risk.py
"""Score de riesgo (07 · §4)."""

from collections.abc import Iterable, Mapping

from app.models.enums import SEVERITY_ORDER, SeverityLevel

W_FAILURE, W_ANOMALY, W_RULES = 0.45, 0.35, 0.20
SEVERITY_WEIGHT: dict[SeverityLevel, float] = {
    SeverityLevel.low: 0.25,
    SeverityLevel.medium: 0.5,
    SeverityLevel.high: 0.75,
    SeverityLevel.critical: 1.0,
}
LEVELS = [SeverityLevel.low, SeverityLevel.medium, SeverityLevel.high, SeverityLevel.critical]
ZSCORE_FEATURES = ("cpu_percent_zscore_60m", "mem_percent_zscore_60m", "latency_ms_zscore_60m")
CONTEXT_CYCLES = 3


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def rule_signal(severities: Iterable[SeverityLevel]) -> float:
    """Máxima severidad de reglas activas del host, normalizada."""
    return max((SEVERITY_WEIGHT[s] for s in severities), default=0.0)


def combine(failure_probability: float | None, anomaly_score: float | None, rules: float) -> float:
    """0.45·P(fallo) + 0.35·anomalía + 0.20·reglas.

    Sin clasificador (`failure_probability=None`) los pesos restantes se renormalizan
    para que el score siga cubriendo 0–1 (modo solo reglas + z-score).
    """
    parts = [(W_RULES, rules)]
    if failure_probability is not None:
        parts.append((W_FAILURE, failure_probability))
    if anomaly_score is not None:
        parts.append((W_ANOMALY, anomaly_score))
    total = sum(w for w, _ in parts)
    return round(clamp01(sum(w * clamp01(v) for w, v in parts) / total), 4)


def risk_level(score: float) -> SeverityLevel:
    if score >= 0.80:
        return SeverityLevel.critical
    if score >= 0.60:
        return SeverityLevel.high
    if score >= 0.30:
        return SeverityLevel.medium
    return SeverityLevel.low


def escalate(level: SeverityLevel) -> SeverityLevel:
    return LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]


def adjust_for_context(
    level: SeverityLevel, environment: str, previous_levels: list[SeverityLevel]
) -> SeverityLevel:
    """+1 nivel en `prod` si el riesgo (≥ medio) se sostiene 3 ciclos seguidos."""
    recent = previous_levels[: CONTEXT_CYCLES - 1]
    sustained = len(recent) == CONTEXT_CYCLES - 1 and all(
        SEVERITY_ORDER[p] >= SEVERITY_ORDER[SeverityLevel.medium] for p in recent
    )
    if environment == "prod" and level != SeverityLevel.low and sustained:
        return escalate(level)
    return level


def fallback_anomaly(features: Mapping[str, float | None]) -> tuple[float, str | None]:
    """Sin modelo: anomaly_score = min(1, max|z| / 4) y el feature con mayor |z|."""
    zscores = {k: abs(v) for k in ZSCORE_FEATURES if (v := features.get(k)) is not None}
    if not zscores:
        return 0.0, None
    top = max(zscores, key=zscores.__getitem__)
    return round(min(1.0, zscores[top] / 4), 4), top
