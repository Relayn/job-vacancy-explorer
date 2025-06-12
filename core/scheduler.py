# core/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from parsers.hh_parser import HHAPIParser, Vacancy
from core.config import config
from core.database import insert_vacancy, remove_duplicates
from datetime import datetime


def update_vacancies(search_query: str = "Python") -> list[Vacancy]:
    """Обновляет вакансии в базе данных."""
    print(f"[{datetime.now()}] Запуск обновления вакансий...")
    hh_parser = HHAPIParser()
    vacancies = hh_parser.parse_vacancies(search_query)

    # Сохраняем вакансии в базу данных
    for vacancy in vacancies:
        insert_vacancy(vacancy)
    remove_duplicates()
    print(f"[{datetime.now()}] Найдено и сохранено {len(vacancies)} вакансий")
    return vacancies


def start_scheduler():
    """Запускает планировщик задач."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_vacancies, "interval", seconds=config.SCHEDULER_INTERVAL)
    print(
        f"[{datetime.now()}] Планировщик запущен с интервалом {config.SCHEDULER_INTERVAL} секунд."
    )
    scheduler.start()


if __name__ == "__main__":
    update_vacancies()
    # start_scheduler()
    # try:
    #     while True:
    #         pass
    # except (KeyboardInterrupt, SystemExit):
    #     print("Планировщик остановлен.")
