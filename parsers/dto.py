"""Объекты передачи данных (DTO) для приложения."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VacancyDTO(BaseModel):
    """Объект передачи данных для вакансий."""

    title: str
    company: str
    location: Optional[str]
    salary: Optional[str]
    description: Optional[str]
    published_at: datetime
    source: str
    original_url: str

    # Эти поля теперь будут заполняться напрямую парсерами
    salary_min_rub: Optional[int] = None
    salary_max_rub: Optional[int] = None
