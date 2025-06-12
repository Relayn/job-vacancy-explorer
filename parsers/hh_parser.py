import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import sqlite3
from time import sleep

# Константы
HH_API_URL = "https://api.hh.ru/vacancies"
REQUEST_DELAY = 0.5  # Задержка между запросами
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


@dataclass
class Vacancy:
    title: str
    company: str
    location: str
    salary: Optional[str]
    description: str
    published_at: datetime
    source: str = "hh.ru"
    original_url: str = ""  # добавлено новое поле


class HHAPIParser:
    def __init__(self):
        self._init_session()
        self._init_db()

    def _init_session(self):
        """Инициализация HTTP-сессии"""
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}
        )

    def _init_db(self):
        """Инициализация базы данных SQLite"""
        self.conn = sqlite3.connect("vacancies.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        """Создание таблицы вакансий"""
        self.cursor.execute(
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
        self.conn.commit()

    def _parse_salary(self, salary_data: Optional[Dict]) -> Optional[str]:
        """Форматирование данных о зарплате"""
        if not salary_data:
            return None

        salary_from = salary_data.get("from")
        salary_to = salary_data.get("to")
        currency = salary_data.get("currency", "RUR")

        parts = []
        if salary_from:
            parts.append(f"от {salary_from}")
        if salary_to:
            parts.append(f"до {salary_to}")

        return " ".join(parts) + f" {currency}" if parts else None

    def _get_vacancy_description(self, item: Dict) -> str:
        """Получение описания вакансии без дополнительного запроса"""
        snippet = item.get("snippet", {})
        requirement = snippet.get("requirement", "") or snippet.get("requirement", "")
        responsibility = snippet.get("responsibility", "")
        return f"{requirement} {responsibility}".strip()

    def _save_vacancy(self, vacancy: Vacancy):
        """Сохранение вакансии в БД"""
        try:
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO vacancies (
                    title, company, location, salary, 
                    description, published_at, source, original_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    vacancy.title,
                    vacancy.company,
                    vacancy.location,
                    vacancy.salary,
                    vacancy.description,
                    vacancy.published_at.isoformat(),
                    vacancy.source,
                    vacancy.original_url,  # новое значение
                ),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка сохранения в БД: {e}")

    def parse_vacancies(
        self, search_query: str = "Python", area: int = 1
    ) -> List[Vacancy]:
        """Основной метод парсинга вакансий"""
        vacancies = []
        params = {"text": search_query, "area": area, "per_page": 50, "page": 0}

        try:
            while True:
                try:
                    response = self.session.get(HH_API_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
                except requests.RequestException as e:
                    print(f"Ошибка запроса: {e}")
                    break

                if not data.get("items"):
                    break

                for item in data["items"]:
                    try:
                        # Получаем alternate_url или формируем ссылку вручную по id
                        original_url = item.get("alternate_url")
                        if not original_url and "id" in item:
                            original_url = f"https://hh.ru/vacancy/{item['id']}"
                        vacancy = Vacancy(
                            title=item.get("name", ""),
                            company=item["employer"].get("name", ""),
                            location=item["area"].get("name", ""),
                            salary=self._parse_salary(item.get("salary")),
                            description=self._get_vacancy_description(item),
                            published_at=datetime.strptime(
                                item["published_at"], "%Y-%m-%dT%H:%M:%S%z"
                            ),
                            original_url=original_url
                            or "",  # всегда ссылка на вакансию
                        )
                        vacancies.append(vacancy)
                        self._save_vacancy(vacancy)
                    except (KeyError, ValueError) as e:
                        print(f"Пропущена вакансия из-за ошибки в данных: {e}")

                if params["page"] >= data.get("pages", 1) - 1:
                    break

                params["page"] += 1
                sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"Критическая ошибка парсинга: {e}")
        finally:
            return vacancies

    def __del__(self):
        """Закрытие соединений при уничтожении объекта"""
        if hasattr(self, "session"):
            self.session.close()
        if hasattr(self, "conn"):
            self.conn.close()


if __name__ == "__main__":
    parser = HHAPIParser()
    vacancies = parser.parse_vacancies()
    print(f"Найдено и сохранено {len(vacancies)} вакансий")
