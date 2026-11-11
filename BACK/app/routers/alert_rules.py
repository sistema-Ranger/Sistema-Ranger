# BACK/app/routers/alert_rules.py
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AlertRule, User
from app.schemas.query import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate
from app.security.deps import ADMIN_INFRA, NOT_VIEWER, require_roles
from app.services import alert_rules as rule_service

router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])
editors = require_roles(*ADMIN_INFRA)


@router.get("", response_model=list[AlertRuleRead], summary="Listar reglas")
def list_rules(
    db: Session = Depends(get_db), _: User = Depends(require_roles(*NOT_VIEWER))
) -> list[AlertRule]:
    return rule_service.list_rules(db)


@router.post(
    "", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED, summary="Nueva regla"
)
def create_rule(
    data: AlertRuleCreate, db: Session = Depends(get_db), _: User = Depends(editors)
) -> AlertRule:
    return rule_service.create_rule(db, data)


@router.patch("/{rule_id}", response_model=AlertRuleRead, summary="Editar regla")
def update_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(editors),
) -> AlertRule:
    return rule_service.update_rule(db, rule_id, data)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar regla")
def delete_rule(
    rule_id: int, db: Session = Depends(get_db), _: User = Depends(editors)
) -> Response:
    rule_service.delete_rule(db, rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
