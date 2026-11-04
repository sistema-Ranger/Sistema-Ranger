# BACK/app/services/predictions.py
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.errors import not_found
from app.models import Host, ModelRegistry, Prediction
from app.services.dashboard import latest_predictions
from app.services.timeutil import utcnow


def series(
    db: Session, host_id: int | None, start: datetime, end: datetime, limit: int
) -> list[Prediction]:
    stmt = select(Prediction).where(Prediction.ts.between(start, end))
    if host_id is not None:
        stmt = stmt.where(Prediction.host_id == host_id)
    rows = db.scalars(stmt.order_by(Prediction.ts.desc()).limit(limit)).all()
    return list(reversed(rows))


def summary(db: Session, host_id: int | None) -> dict[str, Any]:
    """Riesgo actual (el peor entre hosts si no se indica host) y anomalías desde las 00:00 UTC."""
    latest = latest_predictions(db, host_id)
    worst = max(latest, key=lambda p: p.risk_score, default=None)
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    anomalies = (
        select(func.count())
        .select_from(Prediction)
        .join(Host, Host.id == Prediction.host_id)
        .where(Prediction.is_anomaly.is_(True), Prediction.ts >= today, Host.is_active.is_(True))
    )
    if host_id is not None:
        anomalies = anomalies.where(Prediction.host_id == host_id)
    return {
        "current_risk_level": worst.risk_level if worst else None,
        "risk_score": worst.risk_score if worst else None,
        "failure_probability": worst.failure_probability if worst else None,
        "anomalies_today": db.scalar(anomalies) or 0,
    }


def active_model(db: Session) -> ModelRegistry | None:
    return db.scalar(select(ModelRegistry).where(ModelRegistry.is_active.is_(True)).limit(1))


def activate_model(db: Session, model_id: int) -> ModelRegistry:
    model = db.get(ModelRegistry, model_id)
    if not model:
        raise not_found("Modelo", "MODEL_NOT_FOUND")
    db.execute(update(ModelRegistry).where(ModelRegistry.id != model_id).values(is_active=False))
    model.is_active = True
    db.commit()
    db.refresh(model)
    return model
