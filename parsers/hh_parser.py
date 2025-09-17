"""Парсер для hh.ru с использованием их официального API."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from requests import Session

from parsers.base_parser import BaseParser
from parsers.dto import VacancyDTO

HH_API_URL = "https://api.hh.ru/vacancies"
REQUEST_DELAY = 0.5  # Задержка между запросами
USER_AGENT = "JobVacancyExplorer/1.0 (https://github.com/Relayn/job-vacancy-explorer)"
logger = logging.getLogger(__name__)


class HHParser(BaseParser):
    """Парсер для сайта hh.ru, использующий их официальное API."""

    def __init__(self) -> None:
        """Инициализирует сессию requests."""
        self.session: Session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}
        )

    def __del__(self) -> None:
        """Закрывает сессию requests при уничтожении объекта."""
        if hasattr(self, "session"):
            self.session.close()

    def _format_salary_string(
        self, salary_data: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Форматирует данные о зарплате в единую строку для передачи в DTO.

        Пример: "от 100000 до 150000 RUR".
        """
        if not salary_data:
            return None

        salary_from = salary_data.get("from")
        salary_to = salary_data.get("to")
        currency = salary_data.get("currency", "RUR").upper()

        parts = []
        if salary_from:
            parts.append(f"от {salary_from}")
        if salary_to:
            parts.append(f"до {salary_to}")

        return " ".join(parts) + f" {currency}" if parts else None

    def _get_description_from_snippet(self, item: Dict[str, Any]) -> str:
        """Получает описание вакансии из полей snippet."""
        snippet = item.get("snippet", {})
        requirement = snippet.get("requirement", "") or ""
        responsibility = snippet.get("responsibility", "") or ""
        # Удаляем HTML-теги подсветки
        requirement = requirement.replace("<highlighttext>", "").replace(
            "</highlighttext>", ""
        )
        responsibility = responsibility.replace("<highlighttext>", "").replace(
            "</highlighttext>", ""
        )
        return f"{requirement}\n{responsibility}".strip()

    def parse(self, search_query: str, area: int = 1) -> List[VacancyDTO]:
        """Основной метод парсинга вакансий с hh.ru.

        Args:
            search_query: Поисковый запрос.
            area: ID региона (1 - Москва).

        Returns:
            Список объектов VacancyDTO.
        """
        vacancies_dto = []
        params: Dict[str, Any] = {
            "text": search_query,
            "area": area,
            "per_page": 50,
            "page": 0,
        }

        logger.info("Начало парсинга hh.ru по запросу: '%s'", search_query)

        page = 0
        while True:
            params["page"] = page
            try:
                response = self.session.get(HH_API_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                logger.error("Ошибка запроса к API hh.ru: %s", e)
                break

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                try:
                    salary_str = self._format_salary_string(item.get("salary"))
                    dto = VacancyDTO(
                        title=item.get("name", "Без названия"),
                        company=item.get("employer", {}).get("name", "Не указана"),
                        location=item.get("area", {}).get("name", "Не указан"),
                        salary=salary_str,
                        description=self._get_description_from_snippet(item),
                        published_at=datetime.fromisoformat(item["published_at"]),
                        source="hh.ru",
                        original_url=item["alternate_url"],
                    )
                    vacancies_dto.append(dto)
                except (KeyError, ValueError) as e:
                    logger.warning(
                        "Пропущена вакансия %s из-за ошибки в данных: %s",
                        item.get("id"),
                        e,
                    )

            total_pages = data.get("pages", 1)
            if page >= total_pages - 1:
                break

            page += 1
            time.sleep(REQUEST_DELAY)

        logger.info("Парсинг hh.ru завершен. Найдено %d вакансий.", len(vacancies_dto))
        return vacancies_dto
