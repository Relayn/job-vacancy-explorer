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
        """Форматирует данные о зарплате в единую строку для отображения."""
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
        requirement = (
            (snippet.get("requirement") or "")
            .replace("<highlighttext>", "")
            .replace("</highlighttext>", "")
        )
        responsibility = (
            (snippet.get("responsibility") or "")
            .replace("<highlighttext>", "")
            .replace("</highlighttext>", "")
        )
        return f"{requirement}\n{responsibility}".strip()

    def _parse_api_item(self, item: Dict[str, Any]) -> Optional[VacancyDTO]:
        """Парсит один элемент из ответа API в VacancyDTO с защитой от ошибок."""
        try:
            # Безопасный доступ к вложенным данным с помощью .get()
            employer = item.get("employer") or {}
            area = item.get("area") or {}
            salary_data = item.get("salary")

            return VacancyDTO(
                title=item["name"],  # Название - единственное обязательное поле
                company=employer.get("name", "Компания не указана"),
                location=area.get("name", "Местоположение не указано"),
                salary=self._format_salary_string(salary_data),
                description=self._get_description_from_snippet(item),
                published_at=datetime.fromisoformat(item["published_at"]),
                source="hh.ru",
                original_url=item["alternate_url"],
                salary_min_rub=salary_data.get("from") if salary_data else None,
                salary_max_rub=salary_data.get("to") if salary_data else None,
            )
        except (KeyError, ValueError) as e:
            # Сработает, только если нет ключевых полей (name, url и т.д.)
            logger.warning(
                "Пропущена вакансия %s из-за отсутствия ключевых полей: %s",
                item.get("id"),
                e,
            )
            return None

    def parse(self, search_query: str, area: int = 1) -> List[VacancyDTO]:
        """Основной метод парсинга вакансий с hh.ru."""
        vacancies_dto = []
        params: Dict[str, Any] = {"text": search_query, "area": area, "per_page": 50}
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
                dto = self._parse_api_item(item)
                if dto:
                    vacancies_dto.append(dto)
            if page >= data.get("pages", 1) - 1:
                break
            page += 1
            time.sleep(REQUEST_DELAY)
        logger.info("Парсинг hh.ru завершен. Найдено %d вакансий.", len(vacancies_dto))
        return vacancies_dto
