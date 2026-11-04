# BACK/app/services/alert_rules.py
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError, not_found
from app.models import AlertRule, Host
from app.schemas.query import AlertRuleCreate, AlertRuleUpdate


def _check_host(db: Session, host_id: int | None) -> None:
    if host_id is not None and not db.get(Host, host_id):
        raise AppError(400, "El host indicado no existe", "INVALID_HOST")


def list_rules(db: Session) -> list[AlertRule]:
    return list(db.scalars(select(AlertRule).order_by(AlertRule.id)))


def get_rule(db: Session, rule_id: int) -> AlertRule:
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise not_found("Regla", "RULE_NOT_FOUND")
    return rule


def create_rule(db: Session, data: AlertRuleCreate) -> AlertRule:
    _check_host(db, data.host_id)
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule_id: int, data: AlertRuleUpdate) -> AlertRule:
    rule = get_rule(db, rule_id)
    changes = data.model_dump(exclude_unset=True)
    if "host_id" in changes:
        _check_host(db, changes["host_id"])
    for field, value in changes.items():
        if value is None and field != "host_id":
            continue
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> None:
    db.delete(get_rule(db, rule_id))
    db.commit()
