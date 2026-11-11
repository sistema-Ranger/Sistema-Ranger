# TEST/ml/test_model_contract.py
"""El artefacto carga y produce probabilidades en [0, 1] con el vector de features esperado."""

from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models import ModelRegistry
from app.worker.model import ModelManager

FEATURES = ["cpu_percent", "mem_percent", "mem_percent_slope_15m"]


def _train_artifact(path: Path) -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(50, 10, size=(200, len(FEATURES)))
    y = (x[:, 1] > 55).astype(int)
    clf = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=10, random_state=0))
    clf.fit(x, y)
    iso = IsolationForest(contamination=0.02, random_state=0).fit(x)
    raw = -iso.score_samples(x)
    joblib.dump(
        {
            "features": FEATURES,
            "classifier": clf,
            "anomaly_model": iso,
            "anomaly_bounds": (float(raw.min()), float(raw.max())),
            "feature_means": dict(zip(FEATURES, x.mean(axis=0), strict=True)),
            "feature_stds": dict(zip(FEATURES, x.std(axis=0), strict=True)),
        },
        path,
    )


def _register(db: Session, artifact: str) -> ModelRegistry:
    record = ModelRegistry(
        name="ranger-risk",
        version="test",
        algorithm="IsolationForest + RandomForestClassifier",
        horizon_minutes=30,
        trained_at=datetime.now(UTC),
        feature_importance={"mem_percent": 0.7, "cpu_percent": 0.3},
        artifact_path=artifact,
        is_active=True,
    )
    db.add(record)
    db.commit()
    return record


def test_model_loads_and_scores_in_unit_interval(db: Session, tmp_path: Path) -> None:
    _train_artifact(tmp_path / "ranger-risk-test.joblib")
    record = _register(db, "ranger-risk-test.joblib")
    manager = ModelManager(str(tmp_path))
    manager.refresh(db)
    assert manager.loaded_id == record.id

    for vector in (
        {"cpu_percent": 50, "mem_percent": 40, "mem_percent_slope_15m": 50},
        {"cpu_percent": 99, "mem_percent": 98, "mem_percent_slope_15m": None},
    ):
        out = manager.score(vector)
        assert 0 <= out.failure_probability <= 1
        assert 0 <= out.anomaly_score <= 1
        assert out.model_id == record.id and out.top_factor in FEATURES
    assert manager.score({"cpu_percent": 50, "mem_percent": 90}).failure_probability > 0.5


def test_missing_artifact_falls_back_to_zscore(db: Session, tmp_path: Path) -> None:
    _register(db, "no-existe.joblib")
    manager = ModelManager(str(tmp_path))
    manager.refresh(db)
    out = manager.score({"cpu_percent_zscore_60m": 4.0})
    assert manager.scorer is None
    assert out.failure_probability is None and out.anomaly_score == 1.0 and out.is_anomaly
