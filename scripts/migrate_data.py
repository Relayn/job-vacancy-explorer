import os
import sqlite3
import sys
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from core.models import Vacancy

# --- Константы ---
# Путь к старой базе данных SQLite
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SQLITE_DB_PATH = os.path.join(project_root, "parsers", "vacancies.db")


def extract_from_sqlite() -> List[Dict[str, Any]]:
    """Извлекает данные из старой базы данных SQLite."""
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"Ошибка: Файл базы данных SQLite не найден по пути: {SQLITE_DB_PATH}")
        return []

    print("Подключение к SQLite...")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Извлечение вакансий из SQLite...")
    cursor.execute("SELECT * FROM vacancies")
    rows = cursor.fetchall()
    conn.close()
    print(f"Найдено {len(rows)} записей в SQLite.")
    return [dict(row) for row in rows]


def transform_and_load(data: List[Dict[str, Any]], db_session):
    """Преобразует данные и загружает их в PostgreSQL."""
    print("Трансформация данных и подготовка к загрузке...")
    vacancies_to_load = []
    processed_urls = set()

    for row in data:
        original_url = row.get("original_url")
        if not original_url or original_url in processed_urls:
            continue

        try:
            published_at_dt = datetime.fromisoformat(row["published_at"])
        except (ValueError, TypeError):
            print(f"Пропущена запись с неверным форматом даты: {row['published_at']}")
            continue

        vacancy = Vacancy(
            title=row["title"],
            company=row["company"],
            location=row["location"],
            salary=row.get("salary"),
            description=row.get("description"),
            published_at=published_at_dt,
            source=row["source"],
            original_url=original_url,
            salary_min_rub=None,
            salary_max_rub=None,
        )
        vacancies_to_load.append(vacancy)
        processed_urls.add(original_url)

    if not vacancies_to_load:
        print("Нет данных для загрузки.")
        return

    print(
        f"Подготовлено {len(vacancies_to_load)} уникальных записей для загрузки в PostgreSQL."
    )

    try:
        print("Загрузка данных в PostgreSQL...")
        db_session.add_all(vacancies_to_load)
        db_session.commit()
        print("Данные успешно загружены в PostgreSQL.")
    except Exception as e:
        print(f"Ошибка при загрузке данных в PostgreSQL: {e}")
        db_session.rollback()


def main():
    """Основная функция для запуска процесса миграции."""
    load_dotenv()

    print("--- Начало миграции данных из SQLite в PostgreSQL ---")

    sqlite_data = extract_from_sqlite()
    if not sqlite_data:
        print("Миграция завершена: нет данных для переноса.")
        return

    print(
        f"Подключение к PostgreSQL по URL: {settings.database_url.replace(settings.DB_PASSWORD, '****')}"
    )
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    transform_and_load(sqlite_data, session)

    session.close()
    print("--- Миграция данных завершена ---")


if __name__ == "__main__":
    main()
