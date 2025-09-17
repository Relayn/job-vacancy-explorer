"""Модели базы данных с использованием ORM SQLAlchemy."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""

    pass


class Vacancy(Base):
    """ORM-модель для хранения вакансий.

    Атрибуты:
        id: Уникальный идентификатор вакансии
        title: Название вакансии
        company: Название компании
        location: Местоположение
        salary: Зарплата в строковом формате
        description: Описание вакансии
        published_at: Дата публикации
        source: Источник вакансии
        original_url: Оригинальная ссылка на вакансию
        salary_min_rub: Минимальная зарплата в рублях
        salary_max_rub: Максимальная зарплата в рублях
        tsvector_search: Поле для полнотекстового поиска
    """

    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    salary: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    original_url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)

    # Поля для нормализованной зарплаты в рублях
    salary_min_rub: Mapped[int] = mapped_column(Integer, nullable=True)
    salary_max_rub: Mapped[int] = mapped_column(Integer, nullable=True)

    # Поле для полнотекстового поиска PostgreSQL
    tsvector_search: Mapped[sa.dialects.postgresql.TSVECTOR] = mapped_column(
        TSVECTOR, nullable=True, index=True
    )

    # Ограничение уникальности для предотвращения дубликатов вакансий
    __table_args__ = (
        UniqueConstraint(
            "title", "company", "published_at", name="_title_company_published_uc"
        ),
    )

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта вакансии."""
        return f"<Vacancy(id={self.id}, title='{self.title}')>"
