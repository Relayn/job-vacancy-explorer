from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import requests

from parsers.dto import VacancyDTO
from parsers.superjob_parser import SuperJobParser

# Мок-ответ HTML от superjob.ru для тестов
MOCK_HTML_RESPONSE = """
<div>
    <!-- 1. Валидная вакансия 1 -->
    <div class="f-test-search-result-item">
        <a href="/vakansii/stazher-inzhener-po-avtomatizacii-testirovaniya-50728083.html">Стажер-инженер по автоматизации тестирования</a>
        <span class="f-test-text-vacancy-item-company-name">OZON: Старт карьеры</span>
        <div><svg><use href="#pin"></use></svg><span>Москва</span></div>
        <div class="f-test-text-company-item-salary">По договорённости</div>
        <span class="_2Q1BH _3doCL _2eclS">Вчера</span>
        <span class="_2Q1BH _3doCL _2k8ZM rtYnN sPJuZ">Описание для Ozon.</span>
    </div>

    <!-- 2. Валидная вакансия 2 -->
    <div class="f-test-search-result-item">
        <a href="/vakansii/veduschij-specialist-informacionnoj-bezopasnosti-49825266.html">Ведущий специалист ИБ</a>
        <span class="f-test-text-vacancy-item-company-name">РТРС</span>
        <div><svg><use href="#pin"></use></svg><span>Москва, улица Академика Королёва</span></div>
        <div class="f-test-text-company-item-salary">от 100 000 ₽</div>
        <span class="_2Q1BH _3doCL _2eclS">Сегодня</span>
        <span class="_2Q1BH _3doCL _2k8ZM rtYnN sPJuZ">Описание для РТРС.</span>
    </div>

    <!-- 3. "Сломанная" вакансия без ссылки -->
    <div class="f-test-search-result-item">
        <span>Что-то без ссылки</span>
    </div>

    <!-- Кнопка "Дальше" -->
    <a class="f-test-button-dalshe" href="?page=2">Дальше</a>
</div>
"""


@pytest.fixture
def mock_requests_get():
    """Фикстура для мокирования requests.get."""
    with patch("requests.Session.get") as mock_get:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = MOCK_HTML_RESPONSE
        mock_get.return_value = mock_response
        yield mock_get


@patch("parsers.superjob_parser.MAX_PAGES", 1)  # Ограничиваем тест одной страницей
def test_superjob_parser_success(mock_requests_get):
    """Тест успешного парсинга вакансий."""
    # Arrange
    parser = SuperJobParser()

    # Act
    vacancies = parser.parse(search_query="Python")

    # Assert
    mock_requests_get.assert_called_once()
    # Должно быть 2 валидных вакансии, одна "сломанная" должна быть пропущена
    assert len(vacancies) == 2
    assert all(isinstance(v, VacancyDTO) for v in vacancies)

    # Проверяем первую вакансию
    v1 = vacancies[0]
    assert v1.title == "Стажер-инженер по автоматизации тестирования"
    assert v1.company == "OZON: Старт карьеры"
    assert v1.location == "Москва"
    assert v1.salary == "По договорённости"

    # Проверяем вторую вакансию
    v2 = vacancies[1]
    assert v2.title == "Ведущий специалист ИБ"
    assert v2.company == "РТРС"
    assert v2.salary == "от 100 000 ₽"


@patch("parsers.superjob_parser.datetime")
def test_date_parsing(mock_datetime_class):
    """Тест внутреннего метода парсинга дат."""
    # Arrange
    # Сохраняем настоящий класс datetime, чтобы использовать его конструктор
    real_datetime_class = datetime

    # Настраиваем мок
    now = real_datetime_class(2025, 7, 20)
    mock_datetime_class.now.return_value = now
    # Перенаправляем вызовы конструктора мока на конструктор реального класса
    mock_datetime_class.side_effect = lambda *args, **kwargs: real_datetime_class(
        *args, **kwargs
    )

    parser = SuperJobParser()

    # Assert
    assert parser._parse_date("Сегодня") == now
    assert parser._parse_date("Вчера") == now - timedelta(days=1)
    assert parser._parse_date("19 июля") == real_datetime_class(2025, 7, 19)
    assert parser._parse_date("Неизвестная дата") == now  # Fallback


def test_superjob_parser_network_error():
    """Тест обработки ошибки сети."""
    # Arrange
    with patch(
        "requests.Session.get",
        side_effect=requests.RequestException("Connection error"),
    ):
        parser = SuperJobParser()
        # Act
        vacancies = parser.parse(search_query="Python")
        # Assert
        assert len(vacancies) == 0
