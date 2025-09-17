"""Pytest configuration and fixtures."""

import os
import sys
from typing import Any, Generator

# --- Импорты сторонних библиотек ---
import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.expression import FunctionElement

# --- Настройка пути проекта ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# --- Импорты локальных модулей приложения ---
from app import create_app  # noqa: E402
from core.config import settings  # noqa: E402
from core.models import Base  # noqa: E402


# --- Компиляция специфичных для диалекта типов для тестирования ---
@compiles(postgresql.TSVECTOR, "sqlite")
def compile_tsvector_for_sqlite(
    element: FunctionElement[Any], compiler: SQLCompiler, **kw: Any
) -> str:
    """Компилирует TSVECTOR как TEXT для диалекта SQLite."""
    return "TEXT"


@pytest.fixture(scope="function")
def setup_test_db() -> Generator[None, None, None]:
    """Фикстура для unit-тестов, зависящих от БД.

    Создает таблицы в тестовой БД (SQLite) перед тестом и удаляет их после.
    """
    if not settings.TEST_DATABASE_URL:
        pytest.fail(
            (
                "TEST_DATABASE_URL is not set. Ensure it's passed via -e flag "
                "for unit tests."
            )
        )

    # Явный assert для mypy, чтобы он знал, что здесь URL не может быть None
    assert settings.TEST_DATABASE_URL is not None
    engine = create_engine(settings.TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def app() -> Generator[Flask, None, None]:
    """Фикстура для создания экземпляра приложения Flask для тестов."""
    _app = create_app()
    _app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test_secret_key",  # Устанавливаем ключ для тестов
        }
    )
    yield _app


@pytest.fixture(scope="module")
def client(app: Flask) -> FlaskClient:
    """Фикстура, предоставляющая тестовый клиент Flask."""
    return app.test_client()
