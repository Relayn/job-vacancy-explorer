"""Парсер для superjob.ru с использованием requests и BeautifulSoup."""

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup, Tag
from requests import Session

from core.config import settings
from parsers.base_parser import BaseParser
from parsers.dto import VacancyDTO
from parsers.utils import parse_salary_string

# Константы
SUPERJOB_BASE_URL = "https://russia.superjob.ru"
REQUEST_DELAY = 1  # Задержка между запросами
USER_AGENT = "JobVacancyExplorer/1.0 (https://github.com/Relayn/job-vacancy-explorer)"
MAX_PAGES = 5
logger = logging.getLogger(__name__)


class SuperJobParser(BaseParser):
    """Парсер для сайта superjob.ru, использующий requests и BeautifulSoup."""

    def __init__(self) -> None:
        """Инициализирует сессию requests и настраивает прокси, если они есть."""
        self.session: Session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
            }
        )
        self.proxies = settings.proxy_list_as_array

    def __del__(self) -> None:
        """Закрывает сессию requests при уничтожении объекта."""
        if hasattr(self, "session"):
            self.session.close()

    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Возвращает случайный прокси из списка."""
        if not self.proxies:
            return None
        proxy_url = random.choice(self.proxies)  # nosec B311
        return {"http": proxy_url, "https": proxy_url}

    def _parse_date(self, date_str: str) -> datetime:
        """Преобразует строку с датой в объект datetime."""
        date_str = date_str.strip().lower()
        if "сегодня" in date_str:
            return datetime.now()
        if "вчера" in date_str:
            return datetime.now() - timedelta(days=1)

        # Обработка формата "19 июля"
        months_map = {
            "января": 1,
            "февраля": 2,
            "марта": 3,
            "апреля": 4,
            "мая": 5,
            "июня": 6,
            "июля": 7,
            "августа": 8,
            "сентября": 9,
            "октября": 10,
            "ноября": 11,
            "декабря": 12,
        }
        parts = date_str.split()
        if len(parts) >= 2 and parts[1] in months_map:
            day = int(parts[0])
            month = months_map[parts[1]]
            year = datetime.now().year
            return datetime(year, month, day)

        return datetime.now()  # Возврат текущей даты, если формат не распознан

    def parse(self, search_query: str) -> List[VacancyDTO]:
        """Основной метод парсинга вакансий с superjob.ru."""
        logger.info("Начало парсинга superjob.ru по запросу: '%s'", search_query)
        vacancies_dto = []
        # quote_plus ожидает строку, гарантируем тип
        encoded_query = quote_plus(str(search_query))

        for page_num in range(1, MAX_PAGES + 1):
            search_url = (
                f"{SUPERJOB_BASE_URL}/vacancy/search/"
                f"?keywords={encoded_query}&page={page_num}"
            )
            logger.info("Парсинг страницы: %s", search_url)

            try:
                response = self.session.get(
                    search_url, proxies=self._get_proxy(), timeout=10
                )
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error("Ошибка при запросе страницы %d: %s", page_num, e)
                break

            soup = BeautifulSoup(response.text, "lxml")
            # Используем новый, более надежный селектор
            vacancy_cards = soup.select("div.f-test-search-result-item")

            if not vacancy_cards:
                logger.info("Вакансии на странице не найдены, завершение парсинга.")
                break

            for card in vacancy_cards:
                dto = self._parse_vacancy_card(card)
                if dto:
                    vacancies_dto.append(dto)

            # Проверка наличия кнопки "Дальше"
            next_page_tag = soup.select_one("a.f-test-button-dalshe")
            if not next_page_tag:
                logger.info("Кнопка 'Дальше' не найдена, это последняя страница.")
                break

            time.sleep(REQUEST_DELAY)

        logger.info(
            "Парсинг superjob.ru завершен. Найдено %d вакансий.",
            len(vacancies_dto),
        )
        return vacancies_dto

    def _parse_vacancy_card(self, card: Tag) -> Optional[VacancyDTO]:
        """Извлекает данные из одной карточки вакансии."""
        try:
            title_tag = card.select_one('a[href*="/vakansii/"]')
            if not title_tag:
                return None
            href_value = title_tag.get("href")
            if not isinstance(href_value, str):
                return None
            title = title_tag.text.strip()
            url = urljoin(SUPERJOB_BASE_URL, href_value)

            company_tag = card.select_one("span.f-test-text-vacancy-item-company-name")
            company = company_tag.text.strip() if company_tag else "Не указана"

            location_pin = card.select_one('svg use[href="#pin"]')
            location = "Не указан"
            if location_pin:
                parent_div = location_pin.find_parent("div")
                if isinstance(parent_div, Tag):
                    location_tag = parent_div.find("span")
                    if location_tag:
                        location = location_tag.text.strip()

            salary_tag = card.select_one(".f-test-text-company-item-salary")
            salary_str = salary_tag.text.strip() if salary_tag else "По договоренности"

            date_tag = card.select_one("span._2Q1BH._3doCL._2eclS")
            published_at = (
                self._parse_date(date_tag.text) if date_tag else datetime.now()
            )

            description_tags = card.select("span._2Q1BH._3doCL._2k8ZM.rtYnN.sPJuZ")
            description = "\n".join(
                [tag.get_text(separator=" ", strip=True) for tag in description_tags]
            )

            # --- Новая логика нормализации зарплаты ---
            salary_min_rub, salary_max_rub = parse_salary_string(salary_str)
            # -------------------------------------------

            return VacancyDTO(
                title=title,
                company=company,
                location=location,
                salary=salary_str,
                description=description,
                published_at=published_at,
                source="superjob.ru",
                original_url=url,
                salary_min_rub=salary_min_rub,
                salary_max_rub=salary_max_rub,
            )
        except (AttributeError, KeyError, ValueError) as e:
            logger.error("Ошибка при парсинге карточки вакансии: %s", e)
            return None
