# BACK/app/routers/__init__.py
from fastapi import APIRouter

from app.routers import (
    alert_rules,
    alerts,
    auth,
    dashboard,
    events,
    hosts,
    incidents,
    ingest,
    metrics,
    predictions,
    reports,
    users,
)

api_router = APIRouter()
for module in (
    auth,
    users,
    hosts,
    ingest,
    metrics,
    events,
    alert_rules,
    alerts,
    incidents,
    predictions,
    dashboard,
    reports,
):
    api_router.include_router(module.router)
