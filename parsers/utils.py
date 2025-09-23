# parsers/utils.py
"""Вспомогательные утилиты для парсеров."""

import re
from typing import Optional, Tuple

from core.config import settings


def parse_salary_string(
    salary_str: Optional[str],
) -> Tuple[Optional[int], Optional[int]]:
    """Парсит строку зарплаты и возвращает (min_salary_rub, max_salary_rub).

    Использует курсы валют из настроек для конвертации в рубли.

    Args:
        salary_str: Строка для парсинга, например "от 50 000 до 80 000 KZT"

    Returns:
        Кортеж с минимальной и максимальной зарплатой в рублях.
    """
    if not salary_str:
        return None, None

    salary_str = salary_str.strip().lower().replace("\u202f", " ").replace("\xa0", " ")

    if "не указана" in salary_str or "договор" in salary_str:
        return None, None

    currency_map = {
        "руб": "RUB",
        "р.": "RUB",
        "₽": "RUB",
        "kzt": "KZT",
        "тенге": "KZT",
        "usd": "USD",
        "$": "USD",
        "eur": "EUR",
        "€": "EUR",
    }
    found_currency = "RUB"
    for key, val in currency_map.items():
        if key in salary_str:
            found_currency = val
            break

    rate = settings.currency_rates.get(found_currency, 1.0)

    numbers = [int(s.replace(" ", "")) for s in re.findall(r"\d[\d\s]*", salary_str)]
    if not numbers:
        return None, None

    min_salary, max_salary = None, None
    if "от" in salary_str and "до" in salary_str and len(numbers) >= 2:
        min_salary, max_salary = min(numbers), max(numbers)
    elif "от" in salary_str and numbers:
        min_salary = numbers[0]
    elif "до" in salary_str and numbers:
        max_salary = numbers[0]
    elif len(numbers) == 1:
        min_salary = max_salary = numbers[0]
    elif len(numbers) >= 2:
        min_salary, max_salary = min(numbers), max(numbers)

    min_salary_rub = int(min_salary * rate) if min_salary else None
    max_salary_rub = int(max_salary * rate) if max_salary else None

    return min_salary_rub, max_salary_rub
