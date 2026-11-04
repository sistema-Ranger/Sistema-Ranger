# BACK/app/services/seed.py
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AlertRule, RuleOperator, SeverityLevel, User, UserRole
from app.security.hashing import hash_password

logger = logging.getLogger(__name__)

# Reglas por defecto (04 · Seed mínimo)
DEFAULT_RULES: list[dict] = [
    {
        "name": "CPU alta sostenida",
        "metric": "cpu_percent",
        "operator": RuleOperator.gt,
        "threshold": 90,
        "duration_minutes": 5,
        "severity": SeverityLevel.high,
    },
    {
        "name": "RAM alta",
        "metric": "mem_percent",
        "operator": RuleOperator.gt,
        "threshold": 85,
        "duration_minutes": 0,
        "severity": SeverityLevel.medium,
    },
    {
        "name": "Disco libre bajo",
        "metric": "disk_free_percent",
        "operator": RuleOperator.lt,
        "threshold": 10,
        "duration_minutes": 0,
        "severity": SeverityLevel.high,
    },
    {
        "name": "Riesgo del modelo alto",
        "metric": "risk_score",
        "operator": RuleOperator.gte,
        "threshold": 0.6,
        "duration_minutes": 0,
        "severity": SeverityLevel.high,
    },
    {
        "name": "Ráfaga de errores",
        "metric": "events_error_count",
        "operator": RuleOperator.gte,
        "threshold": 20,
        "duration_minutes": 5,
        "severity": SeverityLevel.medium,
    },
]


def seed_defaults(db: Session, settings: Settings) -> None:
    """Crea el admin y las reglas por defecto si no existen (idempotente)."""
    if not db.scalar(select(User).where(User.email == settings.admin_email)):
        db.add(
            User(
                email=settings.admin_email,
                full_name="Administrador",
                password_hash=hash_password(settings.admin_password),
                role=UserRole.admin,
            )
        )
        logger.info("Usuario admin creado: %s", settings.admin_email)
    if not db.scalar(select(func.count()).select_from(AlertRule)):
        db.add_all(AlertRule(**rule) for rule in DEFAULT_RULES)
        logger.info("Reglas de alerta por defecto creadas")
    db.commit()
