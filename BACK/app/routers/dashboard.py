# BACK/app/routers/dashboard.py
from typing import Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.query import DashboardOverview
from app.security.deps import get_current_user
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview, summary="KPIs, riesgo, alertas y hosts")
def overview(
    host_id: int | None = None,
    range: Literal["1h", "6h", "24h", "7d"] = "1h",  # noqa: A002  (nombre del contrato)
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    return dashboard_service.overview(db, host_id, range)
