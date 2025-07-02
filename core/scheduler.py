# core/scheduler.py
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from core.config import settings
from core.database import add_vacancies_from_dto, get_db
from parsers.hh_parser import HHParser


def update_vacancies(search_query: str = "Python"):
    """
    Обновляет вакансии в базе данных, используя новую архитектуру.
    1. Вызывает парсер для получения списка DTO.
    2. Передает DTO в функцию для сохранения в БД через SQLAlchemy.
    """
    print(f"[{datetime.now()}] Запуск задачи обновления вакансий...")

    # Шаг 1: Парсинг
    hh_parser = HHParser()
    vacancies_dto_list = hh_parser.parse(search_query)

    if not vacancies_dto_list:
        print(
            f"[{datetime.now()}] Новых вакансий по запросу '{search_query}' не найдено."
        )
        return

    # Шаг 2: Сохранение в БД
    try:
        with get_db() as db:
            added_count = add_vacancies_from_dto(db, vacancies_dto_list)
            print(
                f"[{datetime.now()}] Задача завершена. "
                f"Найдено {len(vacancies_dto_list)} вакансий, "
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
    # Для ручного запуска и отладки
    update_vacancies()
