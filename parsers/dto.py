"""Объекты передачи данных (DTO) для приложения."""

import re
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, model_validator

from core.config import settings


class VacancyDTO(BaseModel):
    """Объект передачи данных для вакансий."""

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
        """Нормализует строку зарплаты в числовые значения в рублях.

        Этот валидатор выполняется до создания экземпляра модели.
        """
        salary_str = values.get("salary")
        if not salary_str or "по договоренности" in salary_str.lower():
            values["salary_min_rub"] = None
            values["salary_max_rub"] = None
            return values

        # --- Получаем курсы валют из конфигурации ---
        currency_rates = settings.currency_rates

        # --- Извлечение чисел и валюты ---
        cleaned_salary_str = salary_str.replace("\u202f", "").replace(" ", "")
        numbers = [int(s) for s in re.findall(r"\d+", cleaned_salary_str)]
        currency = "RUB"  # Валюта по умолчанию
        for code in currency_rates:
            if code.lower() in salary_str.lower():
                currency = code
                break

        rate = currency_rates.get(currency, 1.0)

        # --- Логика парсинга ---
        min_salary, max_salary = None, None
        lower_salary_str = salary_str.lower()

        if numbers:
            # Объединяем два идентичных блока в один
            if ("от" in lower_salary_str and "до" in lower_salary_str) or (
                len(numbers) == 2
            ):
                min_salary = min(numbers)
                max_salary = max(numbers)
            elif "от" in lower_salary_str:
                min_salary = numbers[0]
            elif "до" in lower_salary_str:
                max_salary = numbers[0]
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
