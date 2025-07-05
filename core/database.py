"""Модуль для взаимодействия с базой данных с использованием SQLAlchemy ORM."""

from contextlib import contextmanager
from typing import Generator, List, Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings
from core.models import Vacancy
from parsers.dto import VacancyDTO

# Создаем engine и sessionmaker для всего приложения
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для получения сессии базы данных.
    Гарантирует, что сессия будет закрыта после использования.

    Yields:
        Session: Экземпляр сессии SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_vacancies_from_dto(db: Session, vacancies_dto: List[VacancyDTO]) -> int:
    """
    Добавляет список вакансий в базу данных из DTO.
    Использует PostgreSQL-специфичный ON CONFLICT DO NOTHING для игнорирования дубликатов.

    Args:
        db: Сессия SQLAlchemy.
        vacancies_dto: Список DTO вакансий.

    Returns:
        Количество успешно добавленных (новых) вакансий.
    """
    if not vacancies_dto:
        return 0

    values_to_insert = [dto.model_dump() for dto in vacancies_dto]

    # Используем insert().on_conflict_do_nothing() для эффективной вставки
    stmt = insert(Vacancy).values(values_to_insert)
    stmt = stmt.on_conflict_do_nothing(index_elements=["original_url"])

    result = db.execute(stmt)
    db.commit()

    return result.rowcount


def get_filtered_vacancies(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    query: Optional[str] = None,
    location: Optional[str] = None,
    company: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    source: Optional[str] = None,
    sort_by: str = "published_at",
    sort_order: str = "desc",
) -> List[Vacancy]:
    """
    Получает отфильтрованный и отсортированный список вакансий из БД с пагинацией.
    Использует полнотекстовый поиск PostgreSQL для поля 'query'.

    Args:
        db: Сессия SQLAlchemy.
        page: Номер страницы.
        per_page: Количество элементов на странице.
        query: Текст для полнотекстового поиска.
        location: Фильтр по местоположению.
        company: Фильтр по компании.
        salary_min: Минимальная зарплата.
        salary_max: Максимальная зарплата.
        source: Фильтр по источнику.
        sort_by: Поле для сортировки ('published_at' или 'salary_max_rub').
        sort_order: Направление сортировки ('asc' или 'desc').

    Returns:
        Список ORM-объектов Vacancy.
    """
    stmt = select(Vacancy)
    filters = []

    if query:
        stmt = stmt.where(
            Vacancy.tsvector_search.match(query, postgresql_regconfig="russian")
        )

    if location:
        filters.append(Vacancy.location.ilike(f"%{location}%"))
    if company:
        filters.append(Vacancy.company.ilike(f"%{company}%"))
    if source:
        filters.append(Vacancy.source == source)

    if salary_min is not None:
        filters.append(Vacancy.salary_max_rub >= salary_min)
    if salary_max is not None:
        filters.append(Vacancy.salary_min_rub <= salary_max)

    if filters:
        stmt = stmt.where(*filters)

    order_field = (
        Vacancy.salary_max_rub if sort_by == "salary" else Vacancy.published_at
    )

    if sort_order == "asc":
        order_expression = order_field.asc().nulls_first()
    else:
        order_expression = order_field.desc().nulls_last()

    if query:
        rank = func.ts_rank(
            Vacancy.tsvector_search,
            func.to_tsquery("russian", query.replace(" ", " & ")),
        ).desc()
        stmt = stmt.order_by(rank, order_expression)
    else:
        stmt = stmt.order_by(order_expression)

    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)

    result = db.execute(stmt)
    return result.scalars().all()


def get_total_vacancies_count(
    db: Session,
    query: Optional[str] = None,
    location: Optional[str] = None,
    company: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    source: Optional[str] = None,
) -> int:
    """
    Возвращает общее количество вакансий, соответствующих фильтрам.
    Использует полнотекстовый поиск PostgreSQL для поля 'query'.

    Args:
        db: Сессия SQLAlchemy.
        (остальные параметры аналогичны get_filtered_vacancies)

    Returns:
        Общее количество вакансий.
    """
    stmt = select(func.count()).select_from(Vacancy)
    filters = []

    if query:
        stmt = stmt.where(
            Vacancy.tsvector_search.match(query, postgresql_regconfig="russian")
        )

    if location:
        filters.append(Vacancy.location.ilike(f"%{location}%"))
    if company:
        filters.append(Vacancy.company.ilike(f"%{company}%"))
    if source:
        filters.append(Vacancy.source == source)
    if salary_min is not None:
        filters.append(Vacancy.salary_max_rub >= salary_min)
    if salary_max is not None:
        filters.append(Vacancy.salary_min_rub <= salary_max)

    if filters:
        stmt = stmt.where(*filters)

    result = db.execute(stmt)
    return result.scalar_one()


def get_unique_sources(db: Session) -> List[str]:
    """Возвращает список уникальных источников вакансий."""
    stmt = select(Vacancy.source).distinct().order_by(Vacancy.source)
    result = db.execute(stmt)
    return result.scalars().all()


def get_unique_cities(db: Session) -> List[str]:
    """Возвращает список уникальных городов из вакансий."""
    stmt = (
        select(Vacancy.location)
        .distinct()
        .where(Vacancy.location.isnot(None))
        .order_by(Vacancy.location)
    )
    result = db.execute(stmt)
    return result.scalars().all()
