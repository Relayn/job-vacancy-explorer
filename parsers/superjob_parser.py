import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from core.config import settings
from parsers.base_parser import BaseParser
from parsers.dto import VacancyDTO

# Константы
SUPERJOB_BASE_URL = "https://russia.superjob.ru"
REQUEST_DELAY = 1  # Задержка между запросами для вежливости
USER_AGENT = "JobVacancyExplorer/1.0 (https://github.com/Relayn/job-vacancy-explorer)"
MAX_PAGES = 5


class SuperJobParser(BaseParser):
    """Парсер для сайта superjob.ru, использующий requests и BeautifulSoup."""

    def __init__(self):
        """Инициализирует сессию requests и настраивает прокси, если они есть."""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            }
        )
        self.proxies = settings.proxy_list_as_array

    def __del__(self):
        """Закрывает сессию requests при уничтожении объекта."""
        if hasattr(self, "session"):
            self.session.close()

    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Возвращает случайный прокси из списка."""
        if not self.proxies:
            return None
        proxy_url = random.choice(self.proxies)
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

    def _parse_vacancy_card(self, card: Tag) -> Optional[VacancyDTO]:
        """Извлекает данные из одной карточки вакансии."""
        try:
            # Название и URL
            title_tag = card.select_one('a[href*="/vakansii/"]')
            if not title_tag:
                return None  # Пропускаем, если нет основной ссылки
            title = title_tag.text.strip()
            url = urljoin(SUPERJOB_BASE_URL, title_tag["href"])

            # Компания
            company_tag = card.select_one("span.f-test-text-vacancy-item-company-name")
            company = company_tag.text.strip() if company_tag else "Не указана"

            # Местоположение (ищем span после иконки-пина)
            location_pin = card.select_one('svg use[href="#pin"]')
            location = "Не указан"

            if location_pin:
                location_tag = location_pin.find_next("span")
                if location_tag:
                    location = location_tag.text.strip()

            # Зарплата
            salary_tag = card.select_one(".f-test-text-company-item-salary")
            salary = "По договоренности"
            if salary_tag:
                # Заменяем неразрывные пробелы и удаляем лишнее
                salary = (
                    salary_tag.text.replace("\xa0", " ").replace("/месяц", "").strip()
                )

            # Дата публикации
            date_tag = card.select_one("span._2Q1BH._3doCL._2eclS")
            published_at = (
                self._parse_date(date_tag.text) if date_tag else datetime.now()
            )

            # Описание
            description_tags = card.select("span._2Q1BH._3doCL._2k8ZM.rtYnN.sPJuZ")
            description_parts = [
                tag.get_text(separator=" ", strip=True) for tag in description_tags
            ]
            description = "\n".join(description_parts)

            return VacancyDTO(
                title=title,
                company=company,
                location=location,
                salary=salary,
                description=description,
                published_at=published_at,
                source="superjob.ru",
                original_url=url,
            )
        except (AttributeError, KeyError, ValueError) as e:
            print(f"Ошибка при парсинге карточки вакансии: {e}")
            return None

    def parse(self, search_query: str) -> List[VacancyDTO]:
        """Основной метод парсинга вакансий с superjob.ru."""
        print(
            f"[{datetime.now()}] Начало парсинга superjob.ru по запросу: '{search_query}'"
        )
        vacancies_dto = []
        encoded_query = quote_plus(search_query)

        for page_num in range(1, MAX_PAGES + 1):
            search_url = f"{SUPERJOB_BASE_URL}/vacancy/search/?keywords={encoded_query}&page={page_num}"
            print(f"Парсинг страницы: {search_url}")

            try:
                response = self.session.get(
                    search_url, proxies=self._get_proxy(), timeout=10
                )
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Ошибка при запросе страницы {page_num}: {e}")
                break

            soup = BeautifulSoup(response.text, "lxml")
            # Используем новый, более надежный селектор
            vacancy_cards = soup.select("div.f-test-search-result-item")

            if not vacancy_cards:
                print("Вакансии на странице не найдены, завершение парсинга.")
                break

            for card in vacancy_cards:
                dto = self._parse_vacancy_card(card)
                if dto:
                    vacancies_dto.append(dto)

            # Проверка наличия кнопки "Дальше"
            next_page_tag = soup.select_one("a.f-test-button-dalshe")
            if not next_page_tag:
                print("Кнопка 'Дальше' не найдена, это последняя страница.")
                break

            time.sleep(REQUEST_DELAY)

        print(
            f"[{datetime.now()}] Парсинг superjob.ru завершен. Найдено {len(vacancies_dto)} вакансий."
        )
        return vacancies_dto
