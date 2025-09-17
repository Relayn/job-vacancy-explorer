"""Application configuration settings."""

import json
from typing import Dict, List, Optional

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Manage application settings.

    Loads variables from an .env file.
    """

    # Настройки базы данных PostgreSQL (теперь опциональные)
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
        """Validate that if not using a test DB, all main DB settings are present.

        Returns:
            The validated Settings instance.

        Raises:
            ValueError: If required database settings are missing.
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
        """Return the SQLAlchemy database URL.

        Uses the 'psycopg' dialect for psycopg v3. If TEST_DATABASE_URL is
        set, it will be used instead.

        Returns:
            The database connection URL string.
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
        """Return a list of proxies from the PROXY_LIST string.

        Handles empty values and extra whitespace.

        Returns:
            A list of proxy URLs.
        """
        if not self.PROXY_LIST:
            return []
        return [proxy.strip() for proxy in self.PROXY_LIST.split(",") if proxy.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def currency_rates(self) -> Dict[str, float]:
        """Parse the CURRENCY_RATES_JSON string into a dictionary.

        Returns a default dictionary in case of a parsing error.

        Returns:
            A dictionary of currency rates.
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


# Создаем единственный экземпляр настроек для всего приложения
settings = Settings()
