# TEST/ml/test_features.py
import numpy as np
import pandas as pd
import pytest

from ml.src.features import (
    FEATURE_COLUMNS,
    build_features,
    clean_metrics,
    latest_vector,
    resample_minutely,
    rolling_slope,
)

END = pd.Timestamp("2026-10-15T12:00:00Z")


def minutes(n: int, **cols) -> pd.DataFrame:
    ts = pd.date_range(end=END, periods=n, freq="1min")
    base = {"cpu_percent": 10.0, "mem_percent": 20.0, "disk_percent": 30.0, "is_available": True}
    return pd.DataFrame({"ts": ts, **(base | cols)})


def test_rolling_slope_of_linear_series() -> None:
    series = pd.Series(2.0 * np.arange(30) + 5)
    slope = rolling_slope(series, 15)
    assert slope.iloc[-1] == pytest.approx(2.0)
    assert np.isnan(slope.iloc[0])  # 1 solo punto


def test_rolling_slope_ignores_gaps() -> None:
    series = pd.Series([0.0, 1.0, np.nan, 3.0, 4.0])
    assert rolling_slope(series, 5).iloc[-1] == pytest.approx(1.0)


def test_resample_ffill_limit_and_downtime() -> None:
    df = minutes(3)  # END-2, END-1, END
    df.loc[2, "ts"] = END + pd.Timedelta(minutes=5)  # hueco: END-1 → END+5
    m = resample_minutely(df, END + pd.Timedelta(minutes=8))
    at = lambda minutes: m.loc[END + pd.Timedelta(minutes=minutes)]  # noqa: E731
    assert m.index[-1] == END + pd.Timedelta(minutes=8)
    assert at(1)["cpu_percent"] == 10  # ffill ≤ 2 min
    assert np.isnan(at(2)["cpu_percent"]) and at(2)["is_available"] == 0
    assert at(7)["is_available"] == 1 and at(8)["is_available"] == 0


def test_clean_removes_impossible_values() -> None:
    cleaned = clean_metrics(minutes(2, cpu_percent=[150.0, -5.0]))
    assert cleaned["cpu_percent"].iloc[0] == 100 and np.isnan(cleaned["cpu_percent"].iloc[1])


def test_rolling_and_zscore_features() -> None:
    cpu = [10.0] * 100 + [20.0, 30.0, 40.0, 50.0, 90.0]
    f = build_features(minutes(len(cpu), cpu_percent=cpu))
    last = f.iloc[-1]
    assert list(f.columns) == FEATURE_COLUMNS
    assert last["cpu_percent_mean_5m"] == pytest.approx(46)
    assert last["cpu_percent_max_15m"] == 90
    assert last["cpu_percent_zscore_60m"] > 3
    assert f["cpu_percent_zscore_60m"].iloc[30] != f["cpu_percent_zscore_60m"].iloc[30]  # NaN < 60


def test_memory_slope_feature() -> None:
    mem = list(np.linspace(40, 70, 61))
    last = build_features(minutes(61, mem_percent=mem)).iloc[-1]
    assert last["mem_percent_slope_15m"] == pytest.approx(0.5)
    assert last["mem_percent_slope_60m"] == pytest.approx(0.5)


def test_event_features() -> None:
    def ev(minute: int, level: str, fp: str) -> dict:
        return {"ts": END - pd.Timedelta(minutes=minute), "level": level, "fingerprint": fp}

    events = pd.DataFrame(
        [ev(0, "error", "a"), ev(1, "critical", "b"), ev(2, "error", "a"), ev(10, "warning", "c")]
        + [ev(30, "error", "d")]
    )
    last = build_features(minutes(60), events).iloc[-1]
    assert last["err_count_5m"] == 3
    assert last["crit_count_5m"] == 1
    assert last["warn_count_15m"] == 1
    assert last["distinct_fingerprints_15m"] == 3


def test_empty_input_and_latest_vector() -> None:
    assert build_features(pd.DataFrame()).empty
    vector = latest_vector(build_features(minutes(3)))
    assert set(vector) == set(FEATURE_COLUMNS)
    assert vector["cpu_percent_zscore_60m"] is None and vector["cpu_percent"] == 10
