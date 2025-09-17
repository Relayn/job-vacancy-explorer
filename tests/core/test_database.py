"""Unit tests for database interaction functions."""

from datetime import datetime
from typing import Any, Generator

import pytest
from sqlalchemy.orm import Session

from core.database import (
    SessionLocal,
    add_vacancies_from_dto,
    get_filtered_vacancies,
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
    """Provide a clean database session for each test.

    This fixture depends on `setup_test_db` to get the test engine
    and correctly binds the SessionLocal to it.
    """
    test_engine = setup_test_db
    SessionLocal.configure(bind=test_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def populate_db(db_session: Session) -> None:
    """Create a set of vacancies for testing."""
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
    """Test adding new, unique DTOs."""
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
    """Test that duplicate DTOs are ignored."""
    dtos = [
        VacancyDTO(
            title="Python Developer",
            company="Tech Corp",
            location="Moscow",
            salary="100-150k",
            description=None,  # Добавляем недостающее поле
            published_at=datetime(2025, 1, 1),
            source="hh.ru",
            original_url="http://test.com/1",
        ),
        VacancyDTO(
            title="New Vacancy",
            company="NewCo",
            location="Kazan",
            salary="50000",
            description=None,  # И здесь тоже
            published_at=datetime.now(),
            source="test",
            original_url="http://new.com/2",
        ),
    ]
    added_count = add_vacancies_from_dto(db_session, dtos)
    assert added_count == 1
    assert db_session.query(Vacancy).count() == 5  # 4 from populate_db + 1 new


def test_get_unique_sources(db_session: Session, populate_db: None) -> None:
    """Test retrieving unique, sorted sources."""
    sources = get_unique_sources(db_session)
    assert sources == ["hh.ru", "superjob.ru"]


def test_get_unique_cities(db_session: Session, populate_db: None) -> None:
    """Test retrieving unique, sorted cities."""
    cities = get_unique_cities(db_session)
    assert cities == ["Moscow", "Remote", "SPb"]


def test_get_total_vacancies_count(db_session: Session, populate_db: None) -> None:
    """Test counting vacancies with and without filters."""
    assert get_total_vacancies_count(db_session) == 4
    assert get_total_vacancies_count(db_session, location="Moscow") == 2
    assert get_total_vacancies_count(db_session, company="NonExistent") == 0
    assert get_total_vacancies_count(db_session, salary_min=150000) == 2


def test_get_filtered_vacancies_by_location(
    db_session: Session, populate_db: None
) -> None:
    """Test filtering by location."""
    vacancies = get_filtered_vacancies(db_session, location="Moscow")
    assert len(vacancies) == 2
    assert all(v.location == "Moscow" for v in vacancies)


def test_get_filtered_vacancies_by_salary(
    db_session: Session, populate_db: None
) -> None:
    """Test filtering by salary range."""
    # Salary max is >= 150_000
    vacancies_min = get_filtered_vacancies(db_session, salary_min=150000)
    assert len(vacancies_min) == 2
    assert {v.title for v in vacancies_min} == {"Python Developer", "Java Developer"}

    # Salary min is <= 150_000
    vacancies_max = get_filtered_vacancies(db_session, salary_max=150000)
    assert len(vacancies_max) == 2
    assert {v.title for v in vacancies_max} == {
        "Python Developer",
        "Frontend Developer",
    }


def test_get_filtered_vacancies_sorting(db_session: Session, populate_db: None) -> None:
    """Test sorting by date and salary."""
    # Sort by date (default)
    vacancies_date = get_filtered_vacancies(db_session)
    assert [v.title for v in vacancies_date] == [
        "Data Scientist",
        "Java Developer",
        "Frontend Developer",
        "Python Developer",
    ]

    # Sort by salary
    vacancies_salary = get_filtered_vacancies(
        db_session, sort_by="salary", sort_order="desc"
    )
    # Java (200k), Python (150k), Frontend (120k), Data Scientist (None - last)
    assert [v.title for v in vacancies_salary] == [
        "Java Developer",
        "Python Developer",
        "Frontend Developer",
        "Data Scientist",
    ]


def test_get_filtered_vacancies_pagination(
    db_session: Session, populate_db: None
) -> None:
    """Test pagination."""
    # Get page 2 with 2 items per page (sorted by date desc)
    vacancies = get_filtered_vacancies(db_session, page=2, per_page=2)
    assert len(vacancies) == 2
    assert {v.title for v in vacancies} == {
        "Frontend Developer",
        "Python Developer",
    }
