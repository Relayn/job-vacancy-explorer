# core/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Text, UniqueConstraint
from datetime import datetime


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""

    pass


class Vacancy(Base):
    """ORM-модель для хранения вакансий."""

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

    # Добавляем поля для нормализованной зарплаты
    salary_min_rub: Mapped[int] = mapped_column(Integer, nullable=True)
    salary_max_rub: Mapped[int] = mapped_column(Integer, nullable=True)

    # Уникальный ключ для предотвращения дубликатов
    __table_args__ = (
        UniqueConstraint(
            "title", "company", "published_at", name="_title_company_published_uc"
        ),
    )

    def __repr__(self):
        return f"<Vacancy(id={self.id}, title='{self.title}')>"
