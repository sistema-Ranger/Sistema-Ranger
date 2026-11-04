# BACK/app/services/correlation.py
"""Evidencia, tendencia y detección heurística de cuellos de botella (07 · §5)."""

from collections.abc import Mapping
from typing import Any

import pandas as pd

TREND_EPS = 0.05  # unidades por minuto


class Situation:
    CPU = "Saturación de CPU"
    MEMORY = "Posible fuga de memoria"
    MEMORY_HIGH = "Uso elevado de memoria"
    DISK = "Saturación de almacenamiento"
    ERRORS = "Ráfaga de errores"
    DEPENDENCY = "Dependencia externa / conexiones"
    DEGRADATION = "Degradación progresiva del servicio"
    RISK = "Riesgo de fallo elevado"


ACTIONS = {
    Situation.CPU: (
        "Revisar procesos con mayor consumo y picos de tráfico; evaluar escalar recursos"
    ),
    Situation.MEMORY: (
        "Revisar consumo por proceso, reiniciar servicio de forma controlada y analizar heap"
    ),
    Situation.MEMORY_HIGH: "Revisar consumo de memoria por proceso y límites del servicio",
    Situation.DISK: "Liberar espacio (logs, temporales), revisar rotación de logs, ampliar volumen",
    Situation.ERRORS: (
        "Revisar logs de la aplicación y despliegues recientes; validar dependencias"
    ),
    Situation.DEPENDENCY: "Revisar dependencias externas, pool de conexiones y timeouts",
    Situation.DEGRADATION: (
        "Revisar consumo de recursos, errores de aplicación y conexiones al servicio"
    ),
    Situation.RISK: "Revisar la evidencia del modelo y el estado general del host",
}

METRIC_LABELS = {
    "cpu_percent": "CPU",
    "mem_percent": "Memoria",
    "disk_percent": "Disco",
    "disk_free_percent": "Disco libre",
    "latency_ms": "Latencia",
    "error_rate": "Tasa de error",
    "risk_score": "Riesgo",
    "events_error_count": "Errores en logs",
}

# Categoría de recurso para contar señales distintas en la correlación
METRIC_CATEGORY = {
    "cpu_percent": "cpu",
    "mem_percent": "mem",
    "disk_free_percent": "disk",
    "disk_percent": "disk",
    "latency_ms": "latency",
    "error_rate": "errors",
    "events_error_count": "errors",
    "risk_score": "risk",
}


def trend_of(slope: float | None, eps: float = TREND_EPS) -> str:
    if slope is None or pd.isna(slope):
        return "stable"
    return "rising" if slope > eps else "falling" if slope < -eps else "stable"


def series_slope(series: pd.Series, window: int = 15) -> float | None:
    tail = series.dropna().tail(window)
    if len(tail) < 2:
        return None
    x = pd.Series(range(len(tail)), dtype=float)
    y = tail.reset_index(drop=True)
    var = ((x - x.mean()) ** 2).sum()
    return float(((x - x.mean()) * (y - y.mean())).sum() / var) if var else None


def situation_for_metric(metric: str, features: Mapping[str, Any]) -> str:
    mem_slope = features.get("mem_percent_slope_15m") or 0
    return {
        "cpu_percent": Situation.CPU,
        "mem_percent": Situation.MEMORY if mem_slope > TREND_EPS else Situation.MEMORY_HIGH,
        "disk_free_percent": Situation.DISK,
        "latency_ms": Situation.DEPENDENCY,
        "error_rate": Situation.ERRORS,
        "events_error_count": Situation.ERRORS,
        "risk_score": Situation.RISK,
    }.get(metric, Situation.RISK)


def disk_eta_minutes(features: Mapping[str, Any]) -> float | None:
    slope, disk = features.get("disk_percent_slope_15m"), features.get("disk_percent")
    if not slope or slope <= 0 or disk is None:
        return None
    return round((100 - disk) / slope, 1)


def detect_situation(
    features: Mapping[str, Any], categories: set[str], error_messages: list[str]
) -> str:
    """Heurísticas de cuello de botella para la alerta de correlación."""
    f = {k: (v if v is not None else 0) for k, v in features.items()}
    latency_up = f.get("latency_ms_slope_15m", 0) > 1 or f.get("latency_ms_zscore_60m", 0) > 2
    mem_rising = f.get("mem_percent_slope_15m", 0) > TREND_EPS
    oom = any("memory" in m.lower() or "oom" in m.lower() for m in error_messages)
    resource = {"cpu", "mem", "disk"} & categories
    if len(categories - {"risk"}) >= 3 or (mem_rising and latency_up and "errors" in categories):
        return Situation.DEGRADATION
    if "cpu" in categories and latency_up:
        return Situation.CPU
    if mem_rising and ("mem" in categories or oom):
        return Situation.MEMORY
    if "disk" in categories:
        return Situation.DISK
    if latency_up and "errors" in categories and not resource:
        return Situation.DEPENDENCY
    if "errors" in categories:
        return Situation.ERRORS
    return Situation.DEGRADATION


def metric_evidence(
    metric: str,
    value: float | None,
    minute: pd.DataFrame,
    features: Mapping[str, Any],
    sustained_minutes: int = 0,
    window_minutes: int = 0,
) -> dict[str, Any]:
    """Evidencia legible: [{metric, value, detail}] (ver 05 · GET /alerts/{id})."""
    v = round(float(value), 2) if value is not None else None
    if metric == "cpu_percent":
        detail = f"{v:.0f}% durante {max(sustained_minutes, 1)} min"
    elif metric == "mem_percent":
        trend = {"rising": "ascendente", "falling": "descendente", "stable": "estable"}[
            trend_of(features.get("mem_percent_slope_15m"))
        ]
        detail = f"{v:.0f}% y tendencia {trend}"
    elif metric == "latency_ms":
        start = minute["latency_ms"].dropna().head(1) if "latency_ms" in minute else []
        start_v = float(start.iloc[0]) if len(start) else v
        detail = f"de {start_v:.0f} ms a {v:.0f} ms"
    elif metric == "disk_free_percent":
        eta = disk_eta_minutes(features)
        detail = f"{v:.1f}% libre" + (f", lleno en ~{eta:.0f} min" if eta else "")
    elif metric == "error_rate":
        detail = f"{v:.1f}% de respuestas con error"
    elif metric == "events_error_count":
        detail = f"{v:.0f} eventos error/critical en {max(window_minutes, 1)} min"
    elif metric == "risk_score":
        detail = f"riesgo estimado {v:.2f}"
    else:
        detail = f"{METRIC_LABELS.get(metric, metric)}: {v}"
    return {"metric": metric, "value": v, "detail": detail}


def top_error_evidence(events: pd.DataFrame, limit: int = 3) -> list[dict[str, Any]]:
    """Eventos error/critical agrupados por fingerprint (top 3)."""
    if events is None or events.empty:
        return []
    errors = events[events["level"].isin(["error", "critical"])]
    if errors.empty:
        return []
    grouped = (
        errors.groupby(errors["fingerprint"].fillna(errors["message"]))
        .agg(count=("message", "size"), message=("message", "last"))
        .sort_values("count", ascending=False)
        .head(limit)
    )
    return [
        {"metric": "events", "value": float(row["count"]), "detail": f"{row['message']}"[:200]}
        for _, row in grouped.iterrows()
    ]
