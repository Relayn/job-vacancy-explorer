from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from parsers.dto import VacancyDTO
from parsers.hh_parser import HHParser

# Мок-ответ от API hh.ru для тестов
MOCK_API_RESPONSE = {
    "items": [
        {
            "id": "1",
            "name": "Python Developer",
            "employer": {"name": "Test Company 1"},
            "area": {"name": "Moscow"},
            "salary": {"from": 100000, "to": 150000, "currency": "RUR"},
            "snippet": {
                "requirement": "Experience with <highlighttext>Python</highlighttext>",
                "responsibility": "Develop backend",
            },
            "published_at": "2025-07-01T10:00:00+0300",
            "alternate_url": "https://hh.ru/vacancy/1",
        },
        {
            "id": "2",
            "name": "Data Scientist",
            "employer": {"name": "Test Company 2"},
            "area": {"name": "Saint Petersburg"},
            "salary": None,
            "snippet": {"responsibility": "Analyze data"},
            "published_at": "2025-07-02T11:00:00+0300",
            "alternate_url": "https://hh.ru/vacancy/2",
        },
    ],
    "pages": 1,
    "page": 0,
}


@pytest.fixture
def mock_requests_get():
    """Фикстура для мокирования requests.get."""
    with patch("requests.Session.get") as mock_get:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = MOCK_API_RESPONSE
        mock_get.return_value = mock_response
        yield mock_get


def test_hh_parser_success(mock_requests_get):
    """Тест успешного парсинга вакансий."""
    # Arrange
    parser = HHParser()

    # Act
    vacancies = parser.parse(search_query="Python")

    # Assert
    mock_requests_get.assert_called_once()
    assert len(vacancies) == 2
    assert all(isinstance(v, VacancyDTO) for v in vacancies)

    # Проверяем первую вакансию
    v1 = vacancies[0]
    assert v1.title == "Python Developer"
    assert v1.company == "Test Company 1"
    assert v1.location == "Moscow"
    assert v1.salary == "от 100000 до 150000 RUR"
    assert "Experience with Python" in v1.description  # Проверяем очистку от тегов
    assert v1.published_at == datetime.fromisoformat("2025-07-01T10:00:00+03:00")
    assert v1.source == "hh.ru"
    assert v1.original_url == "https://hh.ru/vacancy/1"

    # Проверяем вторую вакансию (без зарплаты)
    v2 = vacancies[1]
    assert v2.title == "Data Scientist"
    assert v2.salary is None


def test_hh_parser_api_error(mock_requests_get):
    """Тест обработки ошибки от API."""
    # Arrange
    mock_requests_get.side_effect = requests.RequestException("API is down")
    parser = HHParser()

    # Act
    vacancies = parser.parse(search_query="Python")

    # Assert
    assert len(vacancies) == 0


def test_hh_parser_malformed_item(mock_requests_get):
    """Тест на пропуск вакансии с некорректными данными."""
    # Arrange
    malformed_response = {
        "items": [
            MOCK_API_RESPONSE["items"][0],  # Одна валидная вакансия
            {"id": "3", "name": "Broken Vacancy"},  # Вторая "сломанная"
        ],
        "pages": 1,
        "page": 0,
    }
    mock_requests_get.return_value.json.return_value = malformed_response
    parser = HHParser()

    # Act
    vacancies = parser.parse(search_query="Python")

    # Assert
    # Парсер должен пропустить сломанную вакансию и вернуть только валидную
    assert len(vacancies) == 1
    assert vacancies[0].title == "Python Developer"
