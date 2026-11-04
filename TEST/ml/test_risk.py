# TEST/ml/test_risk.py
import pytest

from app.models import SeverityLevel as S
from app.services.risk import (
    adjust_for_context,
    combine,
    escalate,
    fallback_anomaly,
    risk_level,
    rule_signal,
)


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0.0, S.low),
        (0.299, S.low),
        (0.30, S.medium),
        (0.59, S.medium),
        (0.60, S.high),
        (0.79, S.high),
        (0.80, S.critical),
        (1.0, S.critical),
    ],
)
def test_risk_level_thresholds(score: float, level: S) -> None:
    assert risk_level(score) == level


def test_combine_formula_with_model() -> None:
    assert combine(0.68, 0.5, 0.75) == pytest.approx(0.45 * 0.68 + 0.35 * 0.5 + 0.20 * 0.75)
    assert combine(2.0, -1.0, 0.0) == pytest.approx(0.45)  # entradas recortadas a 0–1


def test_combine_without_classifier_renormalizes() -> None:
    assert combine(None, 1.0, 1.0) == 1.0
    assert combine(None, 0.5, 0.0) == pytest.approx(0.35 * 0.5 / 0.55, abs=1e-4)


def test_rule_signal_uses_max_severity() -> None:
    assert rule_signal([]) == 0
    assert rule_signal([S.medium, S.high, S.low]) == 0.75


def test_escalate_caps_at_critical() -> None:
    assert escalate(S.medium) == S.high and escalate(S.critical) == S.critical


def test_context_adjustment_only_in_prod_and_sustained() -> None:
    sustained = [S.medium, S.high]
    assert adjust_for_context(S.medium, "prod", sustained) == S.high
    assert adjust_for_context(S.medium, "dev", sustained) == S.medium
    assert adjust_for_context(S.medium, "prod", [S.medium, S.low]) == S.medium
    assert adjust_for_context(S.medium, "prod", [S.medium]) == S.medium
    assert adjust_for_context(S.low, "prod", sustained) == S.low


def test_fallback_anomaly_from_zscores() -> None:
    assert fallback_anomaly({}) == (0.0, None)
    score, top = fallback_anomaly(
        {
            "cpu_percent_zscore_60m": 1.0,
            "mem_percent_zscore_60m": -3.0,
            "latency_ms_zscore_60m": None,
        }
    )
    assert score == 0.75 and top == "mem_percent_zscore_60m"
    assert fallback_anomaly({"cpu_percent_zscore_60m": 9.0})[0] == 1.0
