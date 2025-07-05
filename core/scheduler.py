from datetime import datetime

from core.config import settings
from core.database import (
    add_vacancies_from_dto,
    get_db,
    get_total_vacancies_count,
)
from core.extensions import scheduler
from parsers.hh_parser import HHParser
from parsers.superjob_parser import SuperJobParser


def update_vacancies(search_query: str = "Python"):
    """Обновляет вакансии в базе данных, последовательно запуская все парсеры."""
    print(
        f"[{datetime.now()}] Запуск задачи обновления вакансий по запросу: '{search_query}'..."
    )
    parsers = [HHParser, SuperJobParser]
    all_vacancies_dto = []
    for parser_class in parsers:
        try:
            parser = parser_class()
            vacancies_from_parser = parser.parse(search_query)
            all_vacancies_dto.extend(vacancies_from_parser)
        except Exception as e:
            print(
                f"[{datetime.now()}] КРИТИЧЕСКАЯ ОШИБКА в парсере {parser_class.__name__}: {e}"
            )
    if not all_vacancies_dto:
        print(f"[{datetime.now()}] Новых вакансий по всем источникам не найдено.")
        return
    try:
        with get_db() as db:
            count_before = get_total_vacancies_count(db)
            add_vacancies_from_dto(db, all_vacancies_dto)
            count_after = get_total_vacancies_count(db)
            added_count = count_after - count_before
            print(
                f"[{datetime.now()}] Задача завершена. "
                f"Всего найдено {len(all_vacancies_dto)} вакансий, "
                f"добавлено {added_count} новых."
            )
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при сохранении вакансий в БД: {e}")


def start_scheduler():
    """
    Добавляет периодическую задачу и запускает планировщик,
    если он еще не запущен.
    """
    if not scheduler.get_job("update_vacancies_job"):
        scheduler.add_job(
            update_vacancies,
            "interval",
            seconds=settings.SCHEDULER_INTERVAL,
            id="update_vacancies_job",
        )
        print(
            f"[{datetime.now()}] Периодическая задача обновления вакансий добавлена. "
            f"Интервал: {settings.SCHEDULER_INTERVAL} секунд."
        )

    if not scheduler.running:
        scheduler.start()
        print(f"[{datetime.now()}] Планировщик запущен.")
