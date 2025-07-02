# parsers/dto.py
import re
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, model_validator


class VacancyDTO(BaseModel):
    """Data Transfer Object для вакансий."""

    title: str
    company: str
    location: Optional[str]
    salary: Optional[str]  # Исходная строка зарплаты
    description: Optional[str]
    published_at: datetime
    source: str
    original_url: str
    salary_min_rub: Optional[int] = None
    salary_max_rub: Optional[int] = None

    @model_validator(mode="before")
    def normalize_salary(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует строковое представление зарплаты в числовые значения в рублях.
        Этот валидатор запускается до создания модели.
        """
        salary_str = values.get("salary")
        if not salary_str or "по договоренности" in salary_str.lower():
            values["salary_min_rub"] = None
            values["salary_max_rub"] = None
            return values

        # --- Курсы валют (упрощенно, для примера на Июль 2025) ---
        # В реальном проекте это должно быть вынесено в конфиг или отдельный сервис
        currency_rates = {
            "USD": 90,
            "EUR": 100,
            "KZT": 0.2,
            "UAH": 2.5,
            "BYN": 30,
            "RUR": 1,
            "RUB": 1,
        }

        # --- Извлечение чисел и валюты ---
        cleaned_salary_str = salary_str.replace("\u202f", "").replace(" ", "")
        numbers = [int(s) for s in re.findall(r"\d+", cleaned_salary_str)]
        currency = "RUB"  # Валюта по умолчанию
        for code in currency_rates:
            if code.lower() in salary_str.lower():
                currency = code
                break

        rate = currency_rates.get(currency, 1)

        # --- Логика парсинга ---
        min_salary, max_salary = None, None
        lower_salary_str = salary_str.lower()

        if numbers:
            if "от" in lower_salary_str and "до" in lower_salary_str:
                min_salary = min(numbers)
                max_salary = max(numbers)
            elif "от" in lower_salary_str:
                min_salary = numbers[0]
            elif "до" in lower_salary_str:
                max_salary = numbers[0]
            elif len(numbers) == 2:  # Диапазон "100-200"
                min_salary = min(numbers)
                max_salary = max(numbers)
            elif len(numbers) == 1:  # Одно число
                min_salary = max_salary = numbers[0]

        # --- Конвертация в рубли ---
        values["salary_min_rub"] = (
            int(min_salary * rate) if min_salary is not None else None
        )
        values["salary_max_rub"] = (
            int(max_salary * rate) if max_salary is not None else None
        )

        return values
