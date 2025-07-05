# tests/conftest.py
import os
import sys

# --- Third-party imports ---
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator

# --- Project Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Local Application Imports ---
from core.config import settings  # noqa: E402
from core.models import Base  # noqa: E402


# --- Dialect-specific type compilation for testing ---
@compiles(postgresql.TSVECTOR, "sqlite")
def compile_tsvector_for_sqlite(
    element: TypeDecorator, compiler: any, **kw: any
) -> str:
    """Compile TSVECTOR as TEXT for the SQLite dialect."""
    return "TEXT"


@pytest.fixture(scope="function")
def setup_test_db():
    """
    Фикстура для unit-тестов, зависящих от БД.
    Создает таблицы в тестовой БД (SQLite) перед тестом и удаляет их после.
    """
    if not settings.TEST_DATABASE_URL:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Ensure it's passed via -e flag for unit tests."
        )

    engine = create_engine(settings.TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
