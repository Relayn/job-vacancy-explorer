"""Тесты для SuperJobParser."""

from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import Mock, patch

import pytest
import requests

from parsers.dto import VacancyDTO
from parsers.superjob_parser import SuperJobParser

# Мок-ответ HTML от superjob.ru для основного теста
MOCK_HTML_RESPONSE = """
<div>
    <!-- 1. Валидная вакансия 1 -->
    <div class="f-test-search-result-item">
        <a href="/vakansii/stazher-50728083.html">
            Стажер-инженер по автоматизации тестирования
        </a>
        <span class="f-test-text-vacancy-item-company-name">
            OZON: Старт карьеры
        </span>
        <div><svg><use href="#pin"></use></svg><span>Москва</span></div>
        <div class="f-test-text-company-item-salary">По договорённости</div>
        <span class="_2Q1BH _3doCL _2eclS">Вчера</span>
        <span class="_2Q1BH _3doCL _2k8ZM rtYnN sPJuZ">Описание для Ozon.</span>
    </div>
    <!-- 2. Валидная вакансия 2 -->
    <div class="f-test-search-result-item">
        <a href="/vakansii/veduschij-specialist-ib-49825266.html">
            Ведущий специалист ИБ
        </a>
        <span class="f-test-text-vacancy-item-company-name">РТРС</span>
        <div><svg><use href="#pin"></use></svg><span>Москва</span></div>
        <div class="f-test-text-company-item-salary">от 100 000 ₽</div>
        <span class="_2Q1BH _3doCL _2eclS">Сегодня</span>
    </div>
    <!-- Кнопка "Дальше" -->
    <a class="f-test-button-dalshe" href="?page=2">Дальше</a>
</div>
"""

# Мок-ответ HTML для теста граничных случаев
MOCK_HTML_EDGE_CASES = """
<div>
    <!-- 1. Вакансия без компании -->
    <div class="f-test-search-result-item">
        <a href="/vakansii/vacancy1.html">Vacancy without company</a>
        <div><svg><use href="#pin"></use></svg><span>Moscow</span></div>
        <div class="f-test-text-company-item-salary">100 000 ₽</div>
        <span class="_2Q1BH _3doCL _2eclS">Сегодня</span>
    </div>
    <!-- 2. Вакансия без локации -->
    <div class="f-test-search-result-item">
        <a href="/vakansii/vacancy2.html">Vacancy without location</a>
        <span class="f-test-text-vacancy-item-company-name">Some Company</span>
    </div>
    <!-- 3. Вакансия без зарплаты -->
    <div class="f-test-search-result-item">
        <a href="/vakansii/vacancy3.html">Vacancy without salary</a>
        <span class="f-test-text-vacancy-item-company-name">Some Company</span>
        <div><svg><use href="#pin"></use></svg><span>Moscow</span></div>
    </div>
</div>
"""


@pytest.fixture
def mock_requests_get() -> Generator[Mock, None, None]:
    """Фикстура для мокирования requests.get."""
    with patch("requests.Session.get") as mock_get:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = MOCK_HTML_RESPONSE
        mock_get.return_value = mock_response
        yield mock_get


@patch("parsers.superjob_parser.MAX_PAGES", 1)
def test_superjob_parser_success(mock_requests_get: Mock) -> None:
    """Тест успешного парсинга вакансий."""
    parser = SuperJobParser()
    vacancies = parser.parse(search_query="Python")
    assert len(vacancies) == 2
    assert all(isinstance(v, VacancyDTO) for v in vacancies)
    v1 = vacancies[0]
    assert v1.title == "Стажер-инженер по автоматизации тестирования"
    assert v1.company == "OZON: Старт карьеры"
    assert v1.salary == "По договорённости"


@patch("parsers.superjob_parser.MAX_PAGES", 1)
def test_superjob_parser_edge_cases(mock_requests_get: Mock) -> None:
    """Тест парсинга вакансий с отсутствующими полями (граничные случаи)."""
    mock_requests_get.return_value.text = MOCK_HTML_EDGE_CASES
    parser = SuperJobParser()
    vacancies = parser.parse(search_query="Python")
    assert len(vacancies) == 3
    # 1. Без компании
    v1 = vacancies[0]
    assert v1.title == "Vacancy without company"
    assert v1.company == "Не указана"
    # 2. Без локации
    v2 = vacancies[1]
    assert v2.title == "Vacancy without location"
    assert v2.location == "Не указан"
    # 3. Без зарплаты
    v3 = vacancies[2]
    assert v3.title == "Vacancy without salary"
    assert v3.salary == "По договоренности"


@patch("parsers.superjob_parser.datetime")
def test_date_parsing(mock_datetime_class: Mock) -> None:
    """Тест внутреннего метода парсинга дат."""
    real_datetime_class = datetime
    now = real_datetime_class(2025, 7, 20)
    mock_datetime_class.now.return_value = now
    mock_datetime_class.side_effect = lambda *a, **kw: real_datetime_class(*a, **kw)
    parser = SuperJobParser()
    assert parser._parse_date("Сегодня") == now
    assert parser._parse_date("Вчера") == now - timedelta(days=1)
    assert parser._parse_date("19 июля") == real_datetime_class(2025, 7, 19)
    assert parser._parse_date("Неизвестная дата") == now


def test_superjob_parser_network_error() -> None:
    """Тест обработки ошибки сети."""
    with patch(
        "requests.Session.get",
        side_effect=requests.RequestException("Connection error"),
    ):
        parser = SuperJobParser()
        vacancies = parser.parse(search_query="Python")
        assert len(vacancies) == 0


def test_get_proxy_with_proxies_configured() -> None:
    """Тест, что _get_proxy возвращает корректный прокси, если они настроены."""
    proxy_list = ["http://proxy1.com", "http://proxy2.com"]
    proxy_string = ",".join(proxy_list)
    with patch("parsers.superjob_parser.settings.PROXY_LIST", proxy_string):
        parser = SuperJobParser()
        proxy = parser._get_proxy()
        assert proxy is not None
        assert proxy["http"] in proxy_list
        assert proxy["https"] in proxy_list
