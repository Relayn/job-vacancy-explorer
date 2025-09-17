"""Модуль для взаимодействия с базой данных с использованием SQLAlchemy ORM."""

from contextlib import contextmanager
from typing import Generator, List, Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from core.config import settings
from core.models import Vacancy
from parsers.dto import VacancyDTO

# Создаем engine и sessionmaker для всего приложения
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get a database session as a context manager.

    This function provides a transactional scope around a series of
    operations. It ensures that the session is properly closed after use.

    Yields:
        Session: An instance of the SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_vacancies_from_dto(db: Session, vacancies_dto: List[VacancyDTO]) -> int:
    """Add a list of vacancies to the database from DTOs.

    Uses a PostgreSQL-specific ON CONFLICT DO NOTHING clause to efficiently
    ignore duplicate entries based on the 'original_url' unique constraint.

    Args:
        db: The SQLAlchemy session.
        vacancies_dto: A list of VacancyDTO objects.

    Returns:
        The number of newly inserted vacancies.
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
    """Retrieve a paginated, filtered, and sorted list of vacancies.

    This function uses PostgreSQL's full-text search capabilities for the
    'query' field and provides extensive filtering and sorting options.

    Args:
        db: The SQLAlchemy session.
        page: The page number to retrieve.
        per_page: The number of items per page.
        query: The text for full-text search.
        location: The location to filter by.
        company: The company name to filter by.
        salary_min: The minimum salary to filter by.
        salary_max: The maximum salary to filter by.
        source: The vacancy source to filter by.
        sort_by: The field to sort by ('published_at' or 'salary').
        sort_order: The sort direction ('asc' or 'desc').

    Returns:
        A list of Vacancy ORM objects.
    """
    stmt = select(Vacancy)
    filters: list[ColumnElement[bool]] = []

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

    for filter_clause in filters:
        stmt = stmt.where(filter_clause)

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
    return list(result.scalars().all())


def get_total_vacancies_count(
    db: Session,
    query: Optional[str] = None,
    location: Optional[str] = None,
    company: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    source: Optional[str] = None,
) -> int:
    """Return the total number of vacancies matching the given filters.

    Args:
        db: The SQLAlchemy session.
        query: The text for full-text search.
        location: The location to filter by.
        company: The company name to filter by.
        salary_min: The minimum salary to filter by.
        salary_max: The maximum salary to filter by.
        source: The vacancy source to filter by.

    Returns:
        The total count of matching vacancies.
    """
    stmt = select(func.count()).select_from(Vacancy)
    filters: list[ColumnElement[bool]] = []

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

    for filter_clause in filters:
        stmt = stmt.where(filter_clause)

    result = db.execute(stmt)
    count = result.scalar_one()
    assert count is not None
    return count


def get_unique_sources(db: Session) -> List[str]:
    """Return a list of unique vacancy sources."""
    stmt = select(Vacancy.source).distinct().order_by(Vacancy.source)
    result = db.execute(stmt)
    return list(result.scalars().all())


def get_unique_cities(db: Session) -> List[str]:
    """Return a list of unique cities from vacancies."""
    stmt = (
        select(Vacancy.location)
        .distinct()
        .where(Vacancy.location.isnot(None))
        .order_by(Vacancy.location)
    )
    result = db.execute(stmt)
    return list(result.scalars().all())
