# BACK/app/routers/ingest.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ingest import EventsBatch, IngestAccepted, IngestRegister, IngestRegisterResult
from app.schemas.metric import MetricsBatch
from app.security.api_key import require_collector_key
from app.services import ingest as ingest_service

router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(require_collector_key)])


@router.post("/register", response_model=IngestRegisterResult, summary="Upsert del host")
def register(data: IngestRegister, db: Session = Depends(get_db)) -> IngestRegisterResult:
    return IngestRegisterResult(host_id=ingest_service.register_host(db, data).id)


@router.post(
    "/metrics",
    response_model=IngestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Lote de lecturas (máx. 500)",
)
def metrics(batch: MetricsBatch, db: Session = Depends(get_db)) -> IngestAccepted:
    return IngestAccepted(accepted=ingest_service.ingest_metrics(db, batch))


@router.post(
    "/events",
    response_model=IngestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Lote de logs/eventos (máx. 500)",
)
def events(batch: EventsBatch, db: Session = Depends(get_db)) -> IngestAccepted:
    return IngestAccepted(accepted=ingest_service.ingest_events(db, batch))
