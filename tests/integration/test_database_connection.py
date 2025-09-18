"""Integration tests for database connectivity."""

import pytest
from sqlalchemy import text

from core.config import settings
from core.database import get_db


@pytest.mark.integration
def test_postgres_connection() -> None:
    """Проверяет, что приложение может подключиться к PostgreSQL.

    Этот тест должен запускаться в окружении, где настроено
    подключение к реальной БД, а не к тестовой SQLite.
    """
    # Убедимся, что мы не используем тестовую БД
    assert settings.TEST_DATABASE_URL is None, (
        "Интеграционные тесты не должны использовать TEST_DATABASE_URL"
    )

    try:
        with get_db() as db:
            # Выполняем простой запрос, чтобы проверить соединение
            result = db.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
            print("\nУспешное подключение к PostgreSQL.")
    except Exception as e:
        pytest.fail(f"Не удалось подключиться к PostgreSQL: {e}")
