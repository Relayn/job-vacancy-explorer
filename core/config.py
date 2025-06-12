# core/config.py

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

class Config:
    # Пример конфигурации
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'parsers/vacancies.db')
    SCHEDULER_INTERVAL = int(os.getenv('SCHEDULER_INTERVAL', 3600))  # Интервал в секундах

config = Config()


