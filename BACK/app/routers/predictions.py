# BACK/app/routers/predictions.py
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ModelRegistry, Prediction, User
from app.schemas.prediction import ModelRead, PredictionLatest, PredictionPoint, PredictionSummary
from app.security.deps import ADMIN, NOT_VIEWER, get_current_user, require_roles
from app.services import predictions as prediction_service
from app.services.dashboard import latest_predictions
from app.services.timeutil import TimeRange

router = APIRouter(tags=["predictions"])
readers = require_roles(*NOT_VIEWER)


@router.get(
    "/predictions/latest",
    response_model=list[PredictionLatest],
    summary="Última predicción por host",
)
def latest(
    host_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(readers)
) -> list[Prediction]:
    return latest_predictions(db, host_id)


@router.get(
    "/predictions", response_model=list[PredictionPoint], summary="Serie de riesgo en el tiempo"
)
def series(
    host_id: int | None = None,
    time_range: TimeRange = Depends(),
    limit: int = Query(2000, ge=1, le=5000),
    db: Session = Depends(get_db),
    _: User = Depends(readers),
) -> list[Prediction]:
    start, end = time_range.with_defaults(timedelta(hours=24))
    return prediction_service.series(db, host_id, start, end, limit)


@router.get(
    "/predictions/summary", response_model=PredictionSummary, summary="Resumen de riesgo actual"
)
def summary(
    host_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    return prediction_service.summary(db, host_id)


@router.get(
    "/models/active",
    response_model=ModelRead | None,
    summary="Modelo activo (null si aún no hay modelo entrenado)",
)
def active_model(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> ModelRegistry | None:
    return prediction_service.active_model(db)


@router.post("/models/{model_id}/activate", response_model=ModelRead, summary="Activar versión")
def activate(
    model_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(*ADMIN))
) -> ModelRegistry:
    return prediction_service.activate_model(db, model_id)
