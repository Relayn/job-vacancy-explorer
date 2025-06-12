import sqlite3
from sqlite3 import Error
import os
from typing import Any


def get_db_path():
    """Возвращает путь к базе данных."""
    # Получаем абсолютный путь к директории парсеров
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Формируем путь к базе данных
    db_path = os.path.join(base_dir, "..", "parsers", "vacancies.db")
    return db_path


def create_connection() -> Any:
    """Создает соединение с базой данных SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(
            get_db_path()
        )  # Используем правильный путь к базе данных
        return conn
    except Error as e:
        print(
            f"Error of creating connection: {e}"
        )  # Выводим сообщение об ошибке в консоль
    return conn


def migrate_add_original_url_column(conn):
    """Добавляет столбец original_url, если его нет."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(vacancies)")
        columns = [row[1] for row in cursor.fetchall()]
        if "original_url" not in columns:
            cursor.execute(
                "ALTER TABLE vacancies ADD COLUMN original_url TEXT NOT NULL DEFAULT ''"
            )
            conn.commit()
            print("Столбец original_url успешно добавлен.")
    except Error as e:
        print(f"Ошибка миграции original_url: {e}")


def initialize_database() -> None:
    """Инициализирует базу данных и создает таблицы."""
    conn = create_connection()
    if conn is not None:
        # Сначала создаём таблицу, если её нет
        create_table(conn)
        # Затем добавляем столбец original_url, если его нет
        migrate_add_original_url_column(conn)
        conn.close()
    else:
        print("Error! cannot create the database connection.")


def create_table(conn) -> None:
    """Создает таблицу для хранения вакансий."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                salary TEXT,
                description TEXT,
                published_at DATETIME NOT NULL,
                source TEXT NOT NULL,
                original_url TEXT NOT NULL,
                UNIQUE(title, company, published_at)
            )
            """
        )
        conn.commit()
    except Error as e:
        print(f"Error of creating table: {e}")


def insert_vacancy(vacancy) -> None:
    """Добавляет вакансию в базу данных."""
    conn = create_connection()
    sql = """INSERT OR IGNORE INTO vacancies 
             (title, company, location, salary, description, published_at, source, original_url)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
    # Ensure original_url is a full URL
    original_url = vacancy.original_url
    if original_url and not original_url.startswith(("http://", "https://")):
        original_url = "https://" + original_url.lstrip("/")
    param = (
        vacancy.title,
        vacancy.company,
        vacancy.location,
        vacancy.salary,
        vacancy.description,
        vacancy.published_at.isoformat(),
        vacancy.source,
        original_url,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(sql, param)
        conn.commit()
    except Error as e:
        print(f"Error of inserting vacancy: {e}")
        # логирование
    finally:
        conn.close()


def get_all_vacancies(
    page: int = 1,
    per_page: int = 10,
    order_by: str = "id",
    order_direction: str = "ASC",
) -> list:
    """Получает все вакансии из базы данных с поддержкой пагинации."""
    conn = create_connection()
    vacancies = []
    try:
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            f"SELECT * FROM vacancies ORDER BY {order_by} {order_direction} LIMIT ? OFFSET ?",
            (per_page, offset),
        )
        rows = cursor.fetchall()
        for row in rows:
            vacancy = {
                "id": row[0],
                "title": row[1],
                "company": row[2],
                "location": row[3],
                "salary": row[4],
                "description": row[5],
                "published_at": row[6],
                "source": row[7],
                "original_url": row[8],  # новое поле
            }
            vacancies.append(vacancy)
    except Error as e:
        print(f"Error of getting all vacancies: {e}")
    finally:
        conn.close()
    return vacancies


def search_vacancies(query: str) -> list:
    """Ищет вакансии по заданному запросу."""
    conn = create_connection()
    vacancies = []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM vacancies WHERE title LIKE ? OR company LIKE ? OR location LIKE ?",
            ("%" + query + "%", "%" + query + "%", "%" + query + "%"),
        )
        rows = cursor.fetchall()
        for row in rows:
            vacancy = {
                "id": row[0],
                "title": row[1],
                "company": row[2],
                "location": row[3],
                "salary": row[4],
                "description": row[5],
                "published_at": row[6],
                "source": row[7],
                "original_url": row[8],  # новое поле
            }
            vacancies.append(vacancy)
    except Error as e:
        print(f"Error of searching vacancies: {e}")
    finally:
        conn.close()
    return vacancies


def get_filtered_vacancies(
    query="",
    location="",
    company="",
    page=1,
    per_page=50,
    order_by="id",
    order_direction="DESC",
) -> list:
    """
    Получает отфильтрованные вакансии из базы данных с поддержкой пагинации.
    Фильтрация выполняется на уровне SQL запроса для повышения производительности.
    """
    conn = create_connection()
    vacancies = []
    try:
        cursor = conn.cursor()
        # Базовый SQL запрос
        sql = "SELECT id, title, company, location, salary, description, published_at, source, original_url FROM vacancies WHERE 1=1"
        params = []
        # Добавляем условия для фильтрации
        if query:
            sql += " AND (title LIKE ? OR company LIKE ? OR location LIKE ? OR description LIKE ?)"
            params.extend(["%" + query + "%"] * 4)
        if location:
            sql += " AND location LIKE ?"
            params.append("%" + location + "%")
        if company:
            sql += " AND company LIKE ?"
            params.append("%" + company + "%")
        # Добавляем сортировку и пагинацию
        sql += f" ORDER BY {order_by} {order_direction} LIMIT ? OFFSET ?"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        # Выполняем запрос
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        # Преобразуем результаты в список словарей
        for row in rows:
            vacancy = {
                "id": row[0],
                "title": row[1],
                "company": row[2],
                "location": row[3],
                "salary": row[4],
                "description": row[5],
                "published_at": row[6],
                "source": row[7],
                "original_url": row[8],  # новое поле
            }
            vacancies.append(vacancy)
    except Error as e:
        print(f"Error getting filtered vacancies: {e}")
    finally:
        conn.close()
    return vacancies


def get_total_vacancies_count(query="", location="", company="") -> int:
    """
    Возвращает общее количество вакансий, соответствующих заданным фильтрам.
    Используется для пагинации.
    """
    conn = create_connection()
    count = 0

    try:
        cursor = conn.cursor()

        # Базовый SQL запрос для подсчета
        sql = "SELECT COUNT(*) FROM vacancies WHERE 1=1"
        params = []

        # Добавляем условия для фильтрации
        if query:
            sql += " AND (title LIKE ? OR company LIKE ? OR location LIKE ? OR description LIKE ?)"
            params.extend(["%" + query + "%"] * 4)

        if location:
            sql += " AND location LIKE ?"
            params.append("%" + location + "%")

        if company:
            sql += " AND company LIKE ?"
            params.append("%" + company + "%")

        # Выполняем запрос
        cursor.execute(sql, params)
        count = cursor.fetchone()[0]

    except Error as e:
        print(f"Error getting total vacancies count: {e}")
    finally:
        conn.close()

    return count


def remove_duplicates() -> None:
    """Удаляет повторяющиеся записи из таблицы vacancies."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM vacancies
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM vacancies
                    GROUP BY title, company, published_at
                );
            """
            )
            conn.commit()
            print("Дубликаты удалены успешно.")
        except Error as e:
            print(f"Ошибка при удалении дубликатов: {e}")
        finally:
            conn.close()
    else:
        print("Ошибка: не удалось подключиться к базе данных.")


def get_unique_sources() -> list:
    """Возвращает список уникальных источников вакансий."""
    conn = create_connection()
    sources = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT source FROM vacancies")
        rows = cursor.fetchall()
        sources = [row[0] for row in rows]
    except Error as e:
        print(f"Error getting unique sources: {e}")
    finally:
        conn.close()
    return sources


def get_unique_cities() -> list:
    """Возвращает список уникальных городов из вакансий."""
    conn = create_connection()
    cities = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT location FROM vacancies")
        rows = cursor.fetchall()
        cities = [row[0] for row in rows]
    except Error as e:
        print(f"Error getting unique cities: {e}")
    finally:
        conn.close()
    return cities


if __name__ == "__main__":
    # all_vacancies = get_all_vacancies()
    # searching_vacancies = search_vacancies("Junior")
    #
    # for index, vacancy in enumerate(searching_vacancies, start=1):
    #     if index > 10:
    #         break
    #     print(vacancy)
    remove_duplicates()
