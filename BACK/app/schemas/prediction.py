# BACK/app/schemas/prediction.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import SeverityLevel


class PredictionLatest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    host_id: int
    hostname: str
    risk_level: SeverityLevel
    risk_score: float
    failure_probability: float | None
    anomaly_score: float | None
    is_anomaly: bool
    top_factor: str | None
    ts: datetime


class PredictionPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host_id: int
    ts: datetime
    risk_score: float
    risk_level: SeverityLevel
    anomaly_score: float | None
    failure_probability: float | None
    is_anomaly: bool
    top_factor: str | None


class PredictionSummary(BaseModel):
    current_risk_level: SeverityLevel | None
    risk_score: float | None
    failure_probability: float | None
    anomalies_today: int


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    name: str
    version: str
    algorithm: str
    horizon_minutes: int
    trained_at: datetime
    n_samples: int | None
    precision: float | None
    recall: float | None
    f1: float | None
    roc_auc: float | None
    feature_importance: dict[str, float] | None
    is_active: bool
