# tests/parsers/test_dto.py
from datetime import datetime

import pytest

from parsers.dto import VacancyDTO

# Общие данные для всех тестов, чтобы не дублировать их
BASE_VACANCY_DATA = {
    "title": "Test",
    "company": "Test Inc.",
    "location": "Test City",
    "description": "Test desc",
    "published_at": datetime.now(),
    "source": "test",
    "original_url": "http://test.com",
}


@pytest.mark.parametrize(
    "salary_str, expected_min, expected_max",
    [
        # --- Кейсы без зарплаты ---
        (None, None, None),
        ("", None, None),
        ("по договоренности", None, None),
        ("з/п не указана", None, None),
        # --- Кейсы с "от" ---
        ("от 150000 руб.", 150000, None),
        ("от 150 000 RUB", 150000, None),
        ("от 150\u202f000 RUR", 150000, None),  # с неразрывным пробелом
        # --- Кейсы с "до" ---
        ("до 250000 руб.", None, 250000),
        ("до 250 000 RUB", None, 250000),
        # --- Кейсы с диапазоном ---
        ("150000-250000 руб.", 150000, 250000),
        ("150 000-250 000 RUB", 150000, 250000),
        ("от 150000 до 250000 руб.", 150000, 250000),
        # --- Кейсы с точной суммой ---
        ("100000 руб.", 100000, 100000),
        # --- Кейсы с валютой (курсы: USD=90, EUR=100, KZT=0.2) ---
        ("от 2000 USD", 180000, None),
        ("до 3000 EUR", None, 300000),
        ("3000-4000 USD", 270000, 360000),
        ("500000 KZT", 100000, 100000),
        # --- Пограничные кейсы ---
        ("от 0 руб.", 0, None),
        ("без цифр", None, None),
    ],
)
def test_salary_normalization(salary_str, expected_min, expected_max):
    """
    Тестирует логику нормализации зарплаты в VacancyDTO.
    """
    # Arrange
    data = {"salary": salary_str, **BASE_VACANCY_DATA}

    # Act
    dto = VacancyDTO(**data)

    # Assert
    assert dto.salary_min_rub == expected_min
    assert dto.salary_max_rub == expected_max
    assert dto.salary == salary_str  # Проверяем, что исходная строка сохраняется
