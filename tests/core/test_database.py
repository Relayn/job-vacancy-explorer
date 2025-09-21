"""Модульные тесты для функций взаимодействия с базой данных."""

from datetime import datetime
from typing import Any, Generator

import pytest
from sqlalchemy.orm import Session

from core.database import (
    SessionLocal,
    add_vacancies_from_dto,
    get_average_salary_by_city,
    get_filtered_vacancies,
    get_top_companies_by_vacancies,
    get_total_vacancies_count,
    get_unique_cities,
    get_unique_sources,
)
from core.models import Vacancy
from parsers.dto import VacancyDTO


@pytest.fixture
def db_session(
    setup_test_db: Any,
) -> Generator[Session, None, None]:
    """Предоставляет чистую сессию БД для каждого теста."""
    test_engine = setup_test_db
    SessionLocal.configure(bind=test_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def populate_db(db_session: Session) -> None:
    """Создает набор вакансий для тестирования.

    Tech Corp имеет 2 вакансии, остальные по 1, чтобы проверить сортировку.
    """
    vacancies = [
        Vacancy(
            title="Python Developer",
            company="Tech Corp",
            location="Moscow",
            salary="100-150k",
            published_at=datetime(2025, 1, 1),
            source="hh.ru",
            original_url="http://test.com/1",
            salary_min_rub=100000,
            salary_max_rub=150000,
        ),
        Vacancy(
            title="Senior Python Developer",
            company="Tech Corp",
            location="Moscow",
            salary="200-250k",
            published_at=datetime(2025, 1, 5),
            source="hh.ru",
            original_url="http://test.com/5",
            salary_min_rub=200000,
            salary_max_rub=250000,
        ),
        Vacancy(
            title="Java Developer",
            company="Big Blue",
            location="SPb",
            salary="200k",
            published_at=datetime(2025, 1, 3),
            source="superjob.ru",
            original_url="http://test.com/2",
            salary_min_rub=200000,
            salary_max_rub=200000,
        ),
        Vacancy(
            title="Frontend Developer",
            company="Web Solutions",
            location="Moscow",
            salary="от 120k",
            published_at=datetime(2025, 1, 2),
            source="hh.ru",
            original_url="http://test.com/3",
            salary_min_rub=120000,
            salary_max_rub=None,
        ),
        Vacancy(
            title="Data Scientist",
            company="AI Innovations",
            location="Remote",
            salary=None,
            published_at=datetime(2025, 1, 4),
            source="hh.ru",
            original_url="http://test.com/4",
            salary_min_rub=None,
            salary_max_rub=None,
        ),
    ]
    db_session.add_all(vacancies)
    db_session.commit()


def test_add_vacancies_from_dto_success(db_session: Session) -> None:
    """Тест добавления новых, уникальных DTO."""
    dtos = [
        VacancyDTO(
            title="New Vacancy",
            company="NewCo",
            location="Kazan",
            salary="50000",
            description=None,
            published_at=datetime.now(),
            source="test",
            original_url="http://new.com/1",
        )
    ]
    added_count = add_vacancies_from_dto(db_session, dtos)
    assert added_count == 1
    assert db_session.query(Vacancy).count() == 1


def test_add_vacancies_from_dto_duplicates(
    db_session: Session, populate_db: None
) -> None:
    """Тест того, что дубликаты DTO игнорируются."""
    dtos = [
        VacancyDTO(
            title="Python Developer",
            company="Tech Corp",
            location="Moscow",
            salary="100-150k",
            description=None,
            published_at=datetime(2025, 1, 1),
            source="hh.ru",
            original_url="http://test.com/1",
        ),
        VacancyDTO(
            title="New Vacancy",
            company="NewCo",
            location="Kazan",
            salary="50000",
            description=None,
            published_at=datetime.now(),
            source="test",
            original_url="http://new.com/2",
        ),
    ]
    added_count = add_vacancies_from_dto(db_session, dtos)
    assert added_count == 1
    assert db_session.query(Vacancy).count() == 6  # 5 from populate_db + 1 new


def test_get_unique_sources(db_session: Session, populate_db: None) -> None:
    """Тест получения уникальных, отсортированных источников."""
    sources = get_unique_sources(db_session)
    assert sources == ["hh.ru", "superjob.ru"]


def test_get_unique_cities(db_session: Session, populate_db: None) -> None:
    """Тест получения уникальных, отсортированных городов."""
    cities = get_unique_cities(db_session)
    assert cities == ["Moscow", "Remote", "SPb"]


def test_get_total_vacancies_count(db_session: Session, populate_db: None) -> None:
    """Тест подсчета вакансий с фильтрами и без них."""
    assert get_total_vacancies_count(db_session) == 5
    assert get_total_vacancies_count(db_session, location="Moscow") == 3
    assert get_total_vacancies_count(db_session, company="NonExistent") == 0
    assert get_total_vacancies_count(db_session, salary_min=150000) == 3


def test_get_filtered_vacancies_by_location(
    db_session: Session, populate_db: None
) -> None:
    """Тест фильтрации по местоположению."""
    vacancies = get_filtered_vacancies(db_session, location="Moscow")
    assert len(vacancies) == 3
    assert all(v.location == "Moscow" for v in vacancies)


def test_get_filtered_vacancies_by_salary(
    db_session: Session, populate_db: None
) -> None:
    """Тест фильтрации по диапазону зарплаты."""
    # Salary max is >= 150_000
    vacancies_min = get_filtered_vacancies(db_session, salary_min=150000)
    assert len(vacancies_min) == 3
    assert {v.title for v in vacancies_min} == {
        "Senior Python Developer",
        "Java Developer",
        "Python Developer",
    }

    # Salary min is <= 150_000
    vacancies_max = get_filtered_vacancies(db_session, salary_max=150000)
    assert len(vacancies_max) == 2
    assert {v.title for v in vacancies_max} == {
        "Python Developer",
        "Frontend Developer",
    }


def test_get_filtered_vacancies_sorting(db_session: Session, populate_db: None) -> None:
    """Тест сортировки по дате и зарплате."""
    # Sort by date (default desc)
    vacancies_date = get_filtered_vacancies(db_session)
    assert [v.title for v in vacancies_date] == [
        "Senior Python Developer",
        "Data Scientist",
        "Java Developer",
        "Frontend Developer",
        "Python Developer",
    ]

    # Sort by salary desc
    vacancies_salary = get_filtered_vacancies(
        db_session, sort_by="salary", sort_order="desc"
    )
    assert [v.title for v in vacancies_salary] == [
        "Senior Python Developer",
        "Java Developer",
        "Python Developer",
        "Frontend Developer",
        "Data Scientist",
    ]


def test_get_filtered_vacancies_pagination(
    db_session: Session, populate_db: None
) -> None:
    """Тест пагинации."""
    # Get page 2 with 2 items per page (sorted by date desc)
    vacancies = get_filtered_vacancies(db_session, page=2, per_page=2)
    assert len(vacancies) == 2
    assert {v.title for v in vacancies} == {"Java Developer", "Frontend Developer"}


def test_get_top_companies_by_vacancies(db_session: Session, populate_db: None) -> None:
    """Тест получения топа компаний по числу вакансий."""
    top_companies = get_top_companies_by_vacancies(db_session)
    assert len(top_companies) == 4
    assert top_companies[0] == {"company": "Tech Corp", "vacancy_count": 2}


def test_get_average_salary_by_city(db_session: Session, populate_db: None) -> None:
    """Тест расчета средней зарплаты по городам."""
    salaries = get_average_salary_by_city(db_session)
    # Remote не имеет зарплаты, поэтому только 2 города
    assert len(salaries) == 2
    # Проверяем Москву
    moscow_stats = next((s for s in salaries if s["location"] == "Moscow"), None)
    assert moscow_stats is not None
    assert moscow_stats["vacancy_count"] == 3
    # Среднее из (100000, 200000, 120000) = 420000 / 3 = 140000
    assert moscow_stats["avg_min_salary"] == 140000


def test_add_vacancies_from_dto_empty_list(db_session: Session) -> None:
    """Тест, что функция корректно обрабатывает пустой список DTO."""
    added_count = add_vacancies_from_dto(db_session, [])
    assert added_count == 0
    assert db_session.query(Vacancy).count() == 0


def test_get_filtered_vacancies_by_source_and_asc_sort(
    db_session: Session, populate_db: None
) -> None:
    """Тест фильтрации по источнику и сортировки по возрастанию."""
    # Проверка фильтрации по источнику
    vacancies = get_filtered_vacancies(db_session, source="superjob.ru")
    assert len(vacancies) == 1
    assert vacancies[0].company == "Big Blue"

    # Проверка сортировки по дате по возрастанию (самая старая вакансия - первая)
    vacancies_asc = get_filtered_vacancies(db_session, sort_order="asc")
    assert vacancies_asc[0].title == "Python Developer"
