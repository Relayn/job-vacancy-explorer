"""Модуль для взаимодействия с базой данных с использованием SQLAlchemy ORM.

Содержит функции для работы с вакансиями, включая добавление, поиск и фильтрацию.
"""

from contextlib import contextmanager
from typing import Generator, List, Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from core.config import settings
from core.models import Vacancy
from parsers.dto import VacancyDTO

# Создаем engine и sessionmaker для всего приложения один раз при инициализации
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Возвращает сессию базы данных в виде контекстного менеджера.

    Обеспечивает транзакционную область видимости для серии операций.
    Гарантирует корректное закрытие сессии после использования.

    Yields:
        Session: Экземпляр сессии SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_vacancies_from_dto(db: Session, vacancies_dto: List[VacancyDTO]) -> int:
    """Добавляет список вакансий в базу данных из DTO-объектов.

    Использует специфичное для PostgreSQL выражение ON CONFLICT DO NOTHING
    для эффективного пропуска дубликатов на основе ограничения
    уникальности 'original_url'.

    Args:
        db: Сессия SQLAlchemy.
        vacancies_dto: Список объектов VacancyDTO.

    Returns:
        Количество вставленных вакансий.
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
    """Получает отфильтрованный, отсортированный и разбитый на страницы список вакансий.

    Использует возможности полнотекстового поиска PostgreSQL для поля 'query'
    и предоставляет расширенные возможности фильтрации и сортировки.

    Args:
        db: Сессия SQLAlchemy.
        page: Номер страницы (начинается с 1).
        per_page: Количество элементов на странице.
        query: Текст для полнотекстового поиска.
        location: Фильтр по местоположению.
        company: Фильтр по названию компании.
        salary_min: Минимальная зарплата для фильтрации.
        salary_max: Максимальная зарплата для фильтрации.
        source: Фильтр по источнику вакансии.
        sort_by: Поле для сортировки ('published_at' или 'salary').
        sort_order: Направление сортировки ('asc' или 'desc').

    Returns:
        Список ORM-объектов Vacancy.
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
    """Возвращает общее количество вакансий, соответствующих заданным фильтрам.

    Args:
        db: Сессия SQLAlchemy.
        query: Текст для полнотекстового поиска.
        location: Фильтр по местоположению.
        company: Фильтр по названию компании.
        salary_min: Минимальная зарплата для фильтрации.
        salary_max: Максимальная зарплата для фильтрации.
        source: Фильтр по источнику вакансии.

    Returns:
        Общее количество подходящих вакансий.
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
    """Возвращает список уникальных источников вакансий.

    Args:
        db: Сессия SQLAlchemy.

    Returns:
        Список строк с названиями источников.
    """
    stmt = select(Vacancy.source).distinct().order_by(Vacancy.source)
    result = db.execute(stmt)
    return list(result.scalars().all())


def get_unique_cities(db: Session) -> List[str]:
    """Возвращает список уникальных городов из вакансий.

    Args:
        db: Сессия SQLAlchemy.

    Returns:
        Отсортированный список уникальных названий городов.
    """
    stmt = (
        select(Vacancy.location)
        .distinct()
        .where(Vacancy.location.isnot(None))
        .order_by(Vacancy.location)
    )
    result = db.execute(stmt)
    return list(result.scalars().all())
