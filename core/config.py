from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Класс для управления настройками приложения.
    Загружает переменные из .env файла.
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

    # Переменная для тестовой БД
    TEST_DATABASE_URL: Optional[str] = None

    @model_validator(mode="after")
    def validate_db_settings(self) -> "Settings":
        """
        Проверяет, что если не используется тестовая БД, то все
        настройки для основной БД присутствуют.
        """
        if self.TEST_DATABASE_URL:
            # Если используется тестовая БД, остальные проверки не нужны
            return self

        required_fields = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
        missing_fields = [
            field for field in required_fields if getattr(self, field) is None
        ]

        if missing_fields:
            raise ValueError(
                f"Если TEST_DATABASE_URL не задан, следующие переменные окружения обязательны: {', '.join(missing_fields)}"
            )
        return self

    @property
    def database_url(self) -> str:
        """
        Возвращает URL для подключения к базе данных SQLAlchemy.
        Использует диалект 'psycopg' для psycopg v3.
        Если установлена переменная TEST_DATABASE_URL, используется она.
        """
        if self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL

        # Проверка добавлена для надежности, хотя валидатор уже должен был все проверить
        if not all(
            [self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME]
        ):
            raise ValueError(
                "Невозможно сформировать database_url: отсутствуют необходимые настройки БД."
            )

        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def proxy_list_as_array(self) -> List[str]:
        """
        Возвращает список прокси из строки PROXY_LIST.
        Обрабатывает пустые значения и лишние пробелы.
        """
        if not self.PROXY_LIST:
            return []
        return [proxy.strip() for proxy in self.PROXY_LIST.split(",") if proxy.strip()]


# Создаем единственный экземпляр настроек, который будет использоваться во всем приложении
settings = Settings()
