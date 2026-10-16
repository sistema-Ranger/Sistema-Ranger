# TEST/conftest.py
"""Fixtures comunes: BD de prueba `<POSTGRES_DB>_test` migrada con Alembic y limpiada por test."""

import sys
from collections.abc import Callable, Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# En el contenedor ROOT=/code (app y ml cuelgan de ahí); en local hay que añadir BACK/.
for path in (ROOT / "BACK", ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

import app as app_pkg  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.security.hashing import hash_password  # noqa: E402
from app.security.jwt import create_access_token  # noqa: E402

BACK_DIR = Path(app_pkg.__file__).resolve().parents[1]


def _test_url() -> str:
    settings = get_settings()
    if settings.test_database_url:
        return settings.test_database_url
    url = make_url(settings.database_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


def _recreate_database(test_url: str) -> None:
    url = make_url(test_url)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    test_url = _test_url()
    _recreate_database(test_url)
    cfg = Config(str(BACK_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", test_url.replace("%", "%%"))
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    eng = create_engine(test_url)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _get_db
    # Sin context manager: no se ejecuta el lifespan (seed) contra la BD de desarrollo.
    yield TestClient(app)
    app.dependency_overrides.clear()


TEST_PASSWORD = "secret123"


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def _make(role: UserRole = UserRole.viewer, email: str | None = None) -> User:
        user = User(
            email=email or f"{role.value}-{db.query(User).count()}@ranger.test",
            full_name=f"Usuario {role.value}",
            password_hash=hash_password(TEST_PASSWORD),
            role=role,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def auth_headers(make_user: Callable[..., User]) -> Callable[[UserRole], dict[str, str]]:
    def _headers(role: UserRole = UserRole.admin) -> dict[str, str]:
        user = make_user(role)
        return {"Authorization": f"Bearer {create_access_token(user.id, role.value)}"}

    return _headers


@pytest.fixture
def collector_headers() -> dict[str, str]:
    return {"X-Collector-Key": get_settings().collector_api_key}
