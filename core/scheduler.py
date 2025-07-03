from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from core.config import settings
from core.database import add_vacancies_from_dto, get_db
from parsers.hh_parser import HHParser
from parsers.superjob_parser import SuperJobParser


def update_vacancies(search_query: str = "Python"):
    """
    Обновляет вакансии в базе данных, последовательно запуская все парсеры.
    1. Проходит по списку доступных парсеров.
    2. Собирает DTO со всех источников.
    3. Сохраняет объединенный список в БД через SQLAlchemy.
    """
    print(
        f"[{datetime.now()}] Запуск задачи обновления вакансий по запросу: '{search_query}'..."
    )

    parsers = [HHParser, SuperJobParser]
    all_vacancies_dto = []

    for parser_class in parsers:
        try:
            parser = parser_class()
            # Сообщение о начале парсинга теперь находится внутри самого метода parse()
            vacancies_from_parser = parser.parse(search_query)
            all_vacancies_dto.extend(vacancies_from_parser)
        except Exception as e:
            # Логируем ошибку и продолжаем работу с другими парсерами
            print(
                f"[{datetime.now()}] КРИТИЧЕСКАЯ ОШИБКА в парсере {parser_class.__name__}: {e}"
            )

    if not all_vacancies_dto:
        print(f"[{datetime.now()}] Новых вакансий по всем источникам не найдено.")
        return

    # Шаг 2: Сохранение в БД
    try:
        with get_db() as db:
            added_count = add_vacancies_from_dto(db, all_vacancies_dto)
            print(
                f"[{datetime.now()}] Задача завершена. "
                f"Всего найдено {len(all_vacancies_dto)} вакансий, "
                f"добавлено {added_count} новых."
            )
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при сохранении вакансий в БД: {e}")


def start_scheduler():
    """Запускает планировщик задач."""
    scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    scheduler.add_job(update_vacancies, "interval", seconds=settings.SCHEDULER_INTERVAL)
    print(
        f"[{datetime.now()}] Планировщик запущен. "
        f"Интервал обновления: {settings.SCHEDULER_INTERVAL} секунд."
    )
    scheduler.start()


if __name__ == "__main__":
    # --- Блок для прямого запуска скрипта ---
    import os
    import sys

    # 1. Исправляем sys.path, чтобы найти корневую директорию проекта
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 2. Загружаем переменные окружения.
    # Используем локальный импорт, так как он нужен только при прямом запуске.
    from dotenv import load_dotenv

    dotenv_path = os.path.join(project_root, ".env.local")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        load_dotenv()

    # 3. Запускаем основную функцию
    # Перезагружаем модули, которые зависят от переменных окружения,
    # чтобы они использовали свежие значения из .env.local
    import importlib
    from core import config, database

    importlib.reload(config)
    importlib.reload(database)

    # Теперь можно безопасно вызывать функцию
    update_vacancies()
