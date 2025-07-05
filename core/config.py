from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Класс для управления настройками приложения.
    Загружает переменные из .env файла.
    """

    # Настройки базы данных PostgreSQL
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Настройки планировщика
    SCHEDULER_INTERVAL: int = 3600

    # Настройки Flask
    DEBUG: bool = False

    # Настройки прокси (опционально)
    PROXY_LIST: Optional[str] = None

    # Новая переменная для тестовой БД
    TEST_DATABASE_URL: Optional[str] = None

    @property
    def database_url(self) -> str:
        """
        Возвращает URL для подключения к базе данных SQLAlchemy.
        Использует диалект 'psycopg' для psycopg v3.
        Если установлена переменная TEST_DATABASE_URL, используется она.
        """
        if self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
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
