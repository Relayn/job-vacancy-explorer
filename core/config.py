# core/config.py
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

    @property
    def database_url(self) -> str:
        """
        Возвращает URL для подключения к базе данных SQLAlchemy.
        Использует диалект 'psycopg' для psycopg v3.
        """
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


# Создаем единственный экземпляр настроек, который будет использоваться во всем приложении
settings = Settings()
