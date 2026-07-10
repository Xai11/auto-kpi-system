import os
from pathlib import Path

import pytest

# Auto-load .env so TEST_DATABASE_URL works without manual `export`
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _raw in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _raw.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402, F401 — registers all models with Base.metadata
from app.db.base import Base  # noqa: E402

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/kpi_test",
)


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        pytest.skip(
            "PostgreSQL not available; set TEST_DATABASE_URL to enable DB tests"
        )

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):  # type: ignore[no-untyped-def]
    # Wrap each test in an outer transaction that is always rolled back.
    # Session uses join_transaction_mode="create_savepoint" so service-level
    # commit() calls release SAVEPOINTs rather than committing the outer tx.
    connection = db_engine.connect()
    trans = connection.begin()
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        yield session
    trans.rollback()
    connection.close()
