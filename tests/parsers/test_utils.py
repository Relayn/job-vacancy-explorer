"""Тесты для вспомогательных утилит парсеров."""

from typing import Optional, Tuple

import pytest

from parsers.utils import parse_salary_string


@pytest.mark.parametrize(
    ("salary_str", "expected_result"),
    [
        # --- Валидные случаи ---
        ("от 100\xa0000 руб.", (100000, None)),
        ("до 250 000 руб.", (None, 250000)),
        ("150 000-200 000 руб.", (150000, 200000)),
        ("от 1 000 USD", (90000, None)),  # 1000 * 90
        ("до 500 EUR", (None, 50000)),  # 500 * 100
        ("300\u202f000 KZT", (60000, 60000)),  # 300000 * 0.2
        ("50 000", (50000, 50000)),  # Валюта по умолчанию - RUB
        # --- Невалидные и пустые случаи ---
        ("по договоренности", (None, None)),
        ("з/п не указана", (None, None)),
        (None, (None, None)),
        ("", (None, None)),
    ],
)
def test_parse_salary_string(
    salary_str: Optional[str], expected_result: Tuple[Optional[int], Optional[int]]
) -> None:
    """Проверяет корректность парсинга различных форматов строк зарплаты.

    Args:
        salary_str: Входная строка для парсинга.
        expected_result: Ожидаемый кортеж (min_salary_rub, max_salary_rub).
    """
    assert parse_salary_string(salary_str) == expected_result
