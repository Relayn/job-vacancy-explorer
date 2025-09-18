"""Настройки конфигурации приложения."""

import json
from typing import Dict, List, Optional

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Управление настройками приложения.

    Загружает переменные из файла .env.
    """

    # Настройки подключения к PostgreSQL (все поля опциональны)
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = None

    # Настройки планировщика
    SCHEDULER_INTERVAL: int = 3600

    # Настройки Flask
    DEBUG: bool = False

    # Настройки прокси (опционально)
    PROXY_LIST: Optional[str] = None

    # Курсы валют в формате JSON
    CURRENCY_RATES_JSON: str = (
        '{"USD": 90, "EUR": 100, "KZT": 0.2, "UAH": 2.5, "BYN": 30, "RUR": 1, "RUB": 1}'
    )

    # Переменная для тестовой БД
    TEST_DATABASE_URL: Optional[str] = None

    @model_validator(mode="after")
    def validate_db_settings(self) -> "Settings":
        """Проверяет, что при отсутствии тестовой БД указаны все основные настройки.

        Returns:
            Валидированный экземпляр настроек.

        Raises:
            ValueError: Если отсутствуют обязательные настройки БД.
        """
        if self.TEST_DATABASE_URL:
            # Если используется тестовая БД, остальные проверки не нужны
            return self

        required_fields = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
        missing_fields = [
            field for field in required_fields if getattr(self, field) is None
        ]

        if missing_fields:
            msg = (
                "Если TEST_DATABASE_URL не задан, следующие переменные окружения "
                f"обязательны: {', '.join(missing_fields)}"
            )
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Возвращает URL для подключения к базе данных SQLAlchemy.

        Использует диалект 'psycopg' для psycopg v3. Если задан TEST_DATABASE_URL,
        будет использовано его значение.

        Returns:
            Строка подключения к базе данных.
        """
        if self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL

        # Проверка добавлена для надежности, хотя валидатор уже должен был все проверить
        if not all(
            [self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME]
        ):
            raise ValueError(
                "Невозможно сформировать database_url: отсутствуют "
                "необходимые настройки БД."
            )

        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def proxy_list_as_array(self) -> List[str]:
        """Возвращает список прокси из строки PROXY_LIST.

        Обрабатывает пустые значения и лишние пробелы.

        Returns:
            Список URL-адресов прокси-серверов.
        """
        if not self.PROXY_LIST:
            return []
        return [proxy.strip() for proxy in self.PROXY_LIST.split(",") if proxy.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def currency_rates(self) -> Dict[str, float]:
        """Преобразует строку CURRENCY_RATES_JSON в словарь.

        В случае ошибки парсинга возвращает словарь с значениями по умолчанию.

        Returns:
            Словарь с курсами валют.
        """
        try:
            rates = json.loads(self.CURRENCY_RATES_JSON)
            # Убедимся, что все значения являются числами
            return {k: float(v) for k, v in rates.items()}
        except (TypeError, ValueError):
            # В случае ошибки возвращаем безопасные значения по умолчанию
            # ValueError включает в себя json.JSONDecodeError
            return {
                "USD": 90.0,
                "EUR": 100.0,
                "KZT": 0.2,
                "UAH": 2.5,
                "BYN": 30.0,
                "RUR": 1.0,
                "RUB": 1.0,
            }


# Создаем глобальный экземпляр настроек для всего приложения
settings = Settings()
