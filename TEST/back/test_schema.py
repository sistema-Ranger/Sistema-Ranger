# TEST/back/test_schema.py
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.config import get_settings
from app.database import Base
from app.models import AlertRule, User, UserRole
from app.security.hashing import verify_password
from app.services.seed import DEFAULT_RULES, seed_defaults

EXPECTED_TABLES = {
    "users",
    "hosts",
    "metrics",
    "events",
    "alert_rules",
    "model_registry",
    "predictions",
    "alerts",
    "incidents",
    "incident_alerts",
}


def test_migration_creates_all_tables(engine: Engine) -> None:
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_migration_matches_models(engine: Engine) -> None:
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_special_indexes_exist(engine: Engine) -> None:
    with engine.connect() as conn:
        names = set(conn.scalars(text("SELECT indexname FROM pg_indexes")))
        ext = conn.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"))
    assert {"ix_events_msg_trgm", "ux_alerts_active_dedup", "ix_metrics_host_ts"} <= names
    assert ext == 1


def test_seed_is_idempotent(db: Session) -> None:
    settings = get_settings()
    seed_defaults(db, settings)
    seed_defaults(db, settings)
    admins = db.scalars(select(User).where(User.email == settings.admin_email)).all()
    assert len(admins) == 1
    assert admins[0].role == UserRole.admin
    assert verify_password(settings.admin_password, admins[0].password_hash)
    assert len(db.scalars(select(AlertRule)).all()) == len(DEFAULT_RULES)
