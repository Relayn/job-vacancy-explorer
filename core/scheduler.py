"""Background task scheduler and job definitions."""

import logging
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

logger = logging.getLogger(__name__)


def update_vacancies(search_query: str = "Python") -> None:
    """Update vacancies in the database by running all available parsers."""
    logger.info("Запуск задачи обновления вакансий по запросу: '%s'...", search_query)
    parsers = [HHParser, SuperJobParser]
    all_vacancies_dto = []
    for parser_class in parsers:
        try:
            parser = parser_class()
            vacancies_from_parser = parser.parse(search_query)
            all_vacancies_dto.extend(vacancies_from_parser)
        except Exception as e:
            logger.critical(
                "КРИТИЧЕСКАЯ ОШИБКА в парсере %s: %s",
                parser_class.__name__,
                e,
                exc_info=True,
            )
    if not all_vacancies_dto:
        logger.info("Новых вакансий по всем источникам не найдено.")
        return
    try:
        with get_db() as db:
            count_before = get_total_vacancies_count(db)
            add_vacancies_from_dto(db, all_vacancies_dto)
            count_after = get_total_vacancies_count(db)
            added_count = count_after - count_before
            logger.info(
                "Задача завершена. Всего найдено %d вакансий, добавлено %d новых.",
                len(all_vacancies_dto),
                added_count,
            )
    except Exception as e:
        logger.error("Ошибка при сохранении вакансий в БД: %s", e, exc_info=True)


def start_scheduler() -> None:
    """Add the periodic job and start the scheduler if it's not running."""
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
