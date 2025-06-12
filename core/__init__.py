# core/__init__.py

# Этот файл может быть пустым или содержать инициализацию пакета.
# Например, можно импортировать здесь основные модули, чтобы они были доступны при импорте пакета.

from .config import Config
from .database import initialize_database, get_all_vacancies, insert_vacancy, search_vacancies
from .scheduler import start_scheduler


def create_db():
    # Инициализация базы данных
    initialize_database()
