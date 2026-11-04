# BACK/app/worker/model.py
"""Carga del modelo activo (model_registry) y scoring con fallback a z-score.

Contrato del artefacto `.joblib` (dict):
- `features`: list[str] — orden de columnas esperado (subconjunto de FEATURE_COLUMNS).
- `classifier`: estimador con `predict_proba` → `failure_probability`.
- `anomaly_model` (opcional): estimador con `score_samples` (p. ej. IsolationForest).
- `anomaly_bounds` (opcional): (min, max) de `-score_samples` para normalizar a 0–1.
- `anomaly_threshold` (opcional, 0.8): umbral normalizado de `is_anomaly`.
- `feature_means` / `feature_stds` (opcional): para estimar `top_factor` = importancia × |z|.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelRegistry
from app.services.risk import clamp01, fallback_anomaly

logger = logging.getLogger(__name__)
FALLBACK_ANOMALY_THRESHOLD = 0.75  # |z| ≥ 3


@dataclass
class ModelOutput:
    anomaly_score: float
    failure_probability: float | None
    is_anomaly: bool
    top_factor: str | None
    model_id: int | None = None


def fallback_score(features: dict[str, float | None]) -> ModelOutput:
    score, top = fallback_anomaly(features)
    return ModelOutput(score, None, score >= FALLBACK_ANOMALY_THRESHOLD, top)


class ModelScorer:
    def __init__(self, record: ModelRegistry, artifact: dict[str, Any]) -> None:
        self.model_id = record.id
        self.importance: dict[str, float] = record.feature_importance or {}
        self.features: list[str] = list(artifact["features"])
        self.classifier = artifact["classifier"]
        self.anomaly_model = artifact.get("anomaly_model")
        self.bounds = artifact.get("anomaly_bounds")
        self.threshold = float(artifact.get("anomaly_threshold", 0.8))
        self.means: dict[str, float] = artifact.get("feature_means") or {}
        self.stds: dict[str, float] = artifact.get("feature_stds") or {}

    def _vector(self, features: dict[str, float | None]) -> np.ndarray:
        values = [features.get(name) for name in self.features]
        return np.array([[0.0 if v is None else float(v) for v in values]])

    def _top_factor(self, features: dict[str, float | None]) -> str | None:
        def contribution(name: str) -> float:
            value = features.get(name) or 0.0
            std = self.stds.get(name) or 0.0
            z = abs((value - self.means.get(name, 0.0)) / std) if std else 1.0
            return self.importance.get(name, 0.0) * z

        candidates = [n for n in self.features if self.importance.get(n)]
        return max(candidates, key=contribution) if candidates else None

    def score(self, features: dict[str, float | None]) -> ModelOutput:
        x = self._vector(features)
        failure_probability = clamp01(float(self.classifier.predict_proba(x)[0][1]))
        if self.anomaly_model is not None:
            raw = float(-self.anomaly_model.score_samples(x)[0])
            low, high = self.bounds or (raw, raw + 1)
            anomaly = clamp01((raw - low) / (high - low)) if high > low else 0.0
        else:
            anomaly, _ = fallback_anomaly(features)
        return ModelOutput(
            round(anomaly, 4),
            round(failure_probability, 4),
            anomaly >= self.threshold,
            self._top_factor(features) or fallback_anomaly(features)[1],
            self.model_id,
        )


class ModelManager:
    """Mantiene cargado el modelo activo y lo recarga si cambia en model_registry."""

    def __init__(self, model_dir: str) -> None:
        self.model_dir = model_dir
        self.scorer: ModelScorer | None = None
        self.loaded_id: int | None = None
        self.failed_id: int | None = None

    def refresh(self, db: Session) -> None:
        record = db.scalar(select(ModelRegistry).where(ModelRegistry.is_active.is_(True)).limit(1))
        record_id = record.id if record else None
        if record_id == self.loaded_id or (record_id and record_id == self.failed_id):
            return
        self.scorer, self.loaded_id = None, None
        if record is None:
            logger.info("Sin modelo activo: modo reglas + z-score")
            return
        path = record.artifact_path
        if not os.path.isabs(path):
            path = os.path.join(self.model_dir, path)
        try:
            self.scorer = ModelScorer(record, joblib.load(path))
            self.loaded_id, self.failed_id = record.id, None
            logger.info("Modelo cargado: %s v%s", record.name, record.version)
        except Exception:
            self.failed_id = record.id
            logger.exception("No se pudo cargar %s; se usa fallback z-score", path)

    def score(self, features: dict[str, float | None]) -> ModelOutput:
        if self.scorer is None:
            return fallback_score(features)
        try:
            return self.scorer.score(features)
        except Exception:
            logger.exception("Error al puntuar con el modelo; se usa fallback")
            return fallback_score(features)
