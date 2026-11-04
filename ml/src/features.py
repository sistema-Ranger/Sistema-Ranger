# ml/src/features.py
"""Pipeline de features compartido por entrenamiento y worker (07 · ETL).

Entrada: lecturas crudas (o ya agregadas por minuto) y eventos de un host.
Salida: un DataFrame indexado por minuto (UTC) con las columnas de FEATURE_COLUMNS.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

METRIC_COLUMNS = [
    "cpu_percent",
    "mem_percent",
    "disk_percent",
    "net_recv_bps",
    "net_sent_bps",
    "latency_ms",
    "error_rate",
]
PERCENT_COLUMNS = ["cpu_percent", "mem_percent", "disk_percent", "error_rate"]
ROLLING_METRICS = ["cpu_percent", "mem_percent", "latency_ms"]
SLOPE_METRICS = ["mem_percent", "disk_percent", "latency_ms"]
ZSCORE_METRICS = ["cpu_percent", "mem_percent", "latency_ms"]
ROLLING_WINDOWS = (5, 15, 60)
SLOPE_WINDOWS = (15, 60)
FFILL_LIMIT = 2  # minutos
ZSCORE_BASELINE = 1440  # 24 h
ZSCORE_MIN_PERIODS = 60
EVENT_FEATURES = ["err_count_5m", "crit_count_5m", "warn_count_15m", "distinct_fingerprints_15m"]

FEATURE_COLUMNS: list[str] = (
    METRIC_COLUMNS
    + [
        f"{m}_{stat}_{w}m"
        for m in ROLLING_METRICS
        for w in ROLLING_WINDOWS
        for stat in ("mean", "std", "max")
    ]
    + [f"{m}_slope_{w}m" for m in SLOPE_METRICS for w in SLOPE_WINDOWS]
    + [f"{m}_zscore_60m" for m in ZSCORE_METRICS]
    + EVENT_FEATURES
    + ["downtime_minutes_60m", "hour_sin", "hour_cos"]
)


def clean_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    """Recorta valores físicamente imposibles (porcentajes fuera de 0–100, negativos)."""
    df = metrics.copy()
    for col in METRIC_COLUMNS:
        if col not in df:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
        df.loc[df[col] < 0, col] = np.nan
    for col in PERCENT_COLUMNS:
        df[col] = df[col].clip(upper=100)
    if "is_available" not in df:
        df["is_available"] = 1.0
    df["is_available"] = pd.to_numeric(df["is_available"], errors="coerce").astype(float)
    return df


def resample_minutely(metrics: pd.DataFrame, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Media por minuto; forward-fill máx. 2 min; huecos mayores → is_available = 0."""
    df = clean_metrics(metrics)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.set_index("ts").sort_index()[METRIC_COLUMNS + ["is_available"]]
    minute = df.resample("1min").mean()
    if end is not None:
        end = pd.Timestamp(end).tz_convert("UTC").floor("min")
        if len(minute) and end > minute.index[-1]:
            minute = minute.reindex(pd.date_range(minute.index[0], end, freq="1min"))
    minute = minute.ffill(limit=FFILL_LIMIT)
    minute["is_available"] = minute["is_available"].fillna(0.0)
    return minute


def rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """Pendiente (unidades por minuto) de una regresión lineal sobre la ventana, vectorizada."""
    x = pd.Series(np.arange(len(series), dtype=float), index=series.index).where(series.notna())
    roll = {"min_periods": 2}
    mean_x = x.rolling(window, **roll).mean()
    mean_y = series.rolling(window, **roll).mean()
    mean_xy = (x * series).rolling(window, **roll).mean()
    mean_xx = (x * x).rolling(window, **roll).mean()
    var_x = mean_xx - mean_x**2
    slope = (mean_xy - mean_x * mean_y) / var_x
    return slope.where(var_x > 1e-12)


def _event_features(events: pd.DataFrame | None, index: pd.DatetimeIndex) -> pd.DataFrame:
    out = pd.DataFrame(0.0, index=index, columns=EVENT_FEATURES)
    if events is None or events.empty or index.empty:
        return out
    ev = events.copy()
    ev["minute"] = pd.to_datetime(ev["ts"], utc=True).dt.floor("min")
    ev = ev[ev["minute"].between(index[0], index[-1])]
    if ev.empty:
        return out
    counts = ev.pivot_table(index="minute", columns="level", aggfunc="size", fill_value=0)
    counts = counts.reindex(index, fill_value=0)

    def per_level(level: str) -> pd.Series:
        return counts[level] if level in counts else pd.Series(0.0, index=index)

    errors = per_level("error") + per_level("critical")
    out["err_count_5m"] = errors.rolling(5, min_periods=1).sum()
    out["crit_count_5m"] = per_level("critical").rolling(5, min_periods=1).sum()
    out["warn_count_15m"] = per_level("warning").rolling(15, min_periods=1).sum()
    if "fingerprint" in ev and ev["fingerprint"].notna().any():
        presence = (
            ev.dropna(subset=["fingerprint"])
            .pivot_table(index="minute", columns="fingerprint", aggfunc="size", fill_value=0)
            .reindex(index, fill_value=0)
            .gt(0)
            .astype(float)
        )
        out["distinct_fingerprints_15m"] = presence.rolling(15, min_periods=1).max().sum(axis=1)
    return out.astype(float)


def build_features(
    metrics: pd.DataFrame,
    events: pd.DataFrame | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Features por minuto. `metrics` necesita columna `ts` y las de METRIC_COLUMNS;
    `events` necesita `ts`, `level` y opcionalmente `fingerprint`."""
    if metrics.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS, dtype=float)
    m = resample_minutely(metrics, end)
    f = pd.DataFrame(index=m.index)
    for col in METRIC_COLUMNS:
        f[col] = m[col]
    for col in ROLLING_METRICS:
        for w in ROLLING_WINDOWS:
            r = m[col].rolling(w, min_periods=1)
            f[f"{col}_mean_{w}m"] = r.mean()
            f[f"{col}_std_{w}m"] = m[col].rolling(w, min_periods=2).std()
            f[f"{col}_max_{w}m"] = r.max()
    for col in SLOPE_METRICS:
        for w in SLOPE_WINDOWS:
            f[f"{col}_slope_{w}m"] = rolling_slope(m[col], w)
    for col in ZSCORE_METRICS:
        # valor actual vs media/std de las últimas 24 h (mín. 60 muestras de minuto)
        base = m[col].rolling(ZSCORE_BASELINE, min_periods=ZSCORE_MIN_PERIODS)
        mean, std = base.mean(), base.std()
        z = (m[col] - mean) / std
        f[f"{col}_zscore_60m"] = z.where(std > 1e-9, 0.0).where(mean.notna())
    f = f.join(_event_features(events, m.index))
    f["downtime_minutes_60m"] = (1 - m["is_available"]).rolling(60, min_periods=1).sum()
    hours = m.index.hour + m.index.minute / 60
    f["hour_sin"] = np.sin(2 * np.pi * hours / 24)
    f["hour_cos"] = np.cos(2 * np.pi * hours / 24)
    return f[FEATURE_COLUMNS].astype(float)


def latest_vector(features: pd.DataFrame) -> dict[str, float | None]:
    """Última fila como dict JSON-serializable (NaN → None)."""
    if features.empty:
        return {}
    row = features.iloc[-1]
    return {k: (None if pd.isna(v) else round(float(v), 6)) for k, v in row.items()}
