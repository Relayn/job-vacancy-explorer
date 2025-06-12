import pytest
from app.routes import filter_vacancies


@pytest.fixture
def sample_vacancies():
    return [
        {
            "title": "Python Developer",
            "company": "Tech Solutions",
            "location": "Moscow",
            "salary": "от 100000 RUR",
        },
        {
            "title": "Java Engineer",
            "company": "Global Corp",
            "location": "Saint Petersburg",
            "salary": "до 200000 RUR",
        },
        {
            "title": "Senior Python Dev",
            "company": "Innovate Ltd",
            "location": "Moscow",
            "salary": "150000-250000 USD",
        },
        {
            "title": "Frontend Developer",
            "company": "Web Creators",
            "location": "Kazan",
            "salary": None,
        },
        {
            "title": "DevOps Engineer",
            "company": "Tech Solutions",
            "location": "Moscow",
            "salary": "120000 RUR",
        },
        {
            "title": "C++ Developer",
            "company": "Legacy Systems",
            "location": "Saint Petersburg",
            "salary": "без указания",
        },
        {
            "title": "Go Developer",
            "company": "New Stack",
            "location": "Novosibirsk",
            "salary": "",
        },
    ]


class TestFilterVacancies:

    def test_filter_by_query_title(self, sample_vacancies):
        # Arrange
        query = "python"
        # Act
        filtered = filter_vacancies(sample_vacancies, query=query)
        # Assert
        assert len(filtered) == 2
        assert all(query.lower() in v["title"].lower() for v in filtered)

    def test_filter_by_query_company(self, sample_vacancies):
        # Arrange
        query = "tech solutions"
        # Act
        filtered = filter_vacancies(sample_vacancies, query=query)
        # Assert
        assert len(filtered) == 2
        assert all(query.lower() in v["company"].lower() for v in filtered)

    def test_filter_by_query_location(self, sample_vacancies):
        # Arrange
        query = "saint petersburg"
        # Act
        filtered = filter_vacancies(sample_vacancies, query=query)
        # Assert
        assert len(filtered) == 2
        assert all(query.lower() in v["location"].lower() for v in filtered)

    def test_filter_by_location(self, sample_vacancies):
        # Arrange
        location = "moscow"
        # Act
        filtered = filter_vacancies(sample_vacancies, query="", location=location)
        # Assert
        assert len(filtered) == 3
        assert all(location.lower() in v["location"].lower() for v in filtered)

    def test_filter_by_company(self, sample_vacancies):
        # Arrange
        company = "global corp"
        # Act
        filtered = filter_vacancies(sample_vacancies, query="", company=company)
        # Assert
        assert len(filtered) == 1
        assert all(company.lower() in v["company"].lower() for v in filtered)

    def test_filter_by_salary_min(self, sample_vacancies):
        # Arrange
        salary_min = "120000"
        # Act
        filtered = filter_vacancies(sample_vacancies, query="", salary_min=salary_min)
        # Assert
        assert (
            len(filtered) == 3
        )  # Python Dev (100-150), Senior Python (150-250), DevOps (120)
        assert "Python Developer" in [v["title"] for v in filtered]
        assert "Senior Python Dev" in [v["title"] for v in filtered]
        assert "DevOps Engineer" in [v["title"] for v in filtered]

    def test_filter_by_salary_max(self, sample_vacancies):
        # Arrange
        salary_max = "150000"
        # Act
        filtered = filter_vacancies(sample_vacancies, query="", salary_max=salary_max)
        # Assert
        assert (
            len(filtered) == 3
        )  # Python Dev (100-150), Java Engineer (до 200), DevOps (120)
        assert "Python Developer" in [v["title"] for v in filtered]
        assert "Java Engineer" in [v["title"] for v in filtered]
        assert "DevOps Engineer" in [v["title"] for v in filtered]
        assert "Senior Python Dev" not in [v["title"] for v in filtered]

    def test_filter_by_salary_range(self, sample_vacancies):
        # Arrange
        salary_min = "100000"
        salary_max = "130000"
        # Act
        filtered = filter_vacancies(
            sample_vacancies, query="", salary_min=salary_min, salary_max=salary_max
        )
        # Assert
        assert len(filtered) == 2  # Python Dev (100-150), DevOps (120)
        assert "Python Developer" in [v["title"] for v in filtered]
        assert "DevOps Engineer" in [v["title"] for v in filtered]
        assert "Senior Python Dev" not in [v["title"] for v in filtered]

    def test_filter_by_salary_non_numeric(self, sample_vacancies):
        # Arrange
        salary_min = "100"
        # Act
        filtered = filter_vacancies(sample_vacancies, query="", salary_min=salary_min)
        # Assert
        # Should exclude 'без указания' and None/empty salaries
        assert "C++ Developer" not in [v["title"] for v in filtered]
        assert "Frontend Developer" not in [v["title"] for v in filtered]
        assert "Go Developer" not in [v["title"] for v in filtered]
        assert (
            len(filtered) == 4
        )  # Python Dev (100-150), Java Engineer (до 200), Senior Python (150-250), DevOps (120)

    def test_filter_combinations(self, sample_vacancies):
        # Arrange
        query = "python"
        location = "moscow"
        salary_min = "140000"
        # Act
        filtered = filter_vacancies(
            sample_vacancies, query=query, location=location, salary_min=salary_min
        )
        # Assert
        assert len(filtered) == 1
        assert filtered[0]["title"] == "Senior Python Dev"

    def test_filter_empty_vacancies_list(self):
        # Arrange
        vacancies = []
        query = "test"
        # Act
        filtered = filter_vacancies(vacancies, query=query)
        # Assert
        assert len(filtered) == 0

    def test_filter_no_match(self, sample_vacancies):
        # Arrange
        query = "nonexistent"
        # Act
        filtered = filter_vacancies(sample_vacancies, query=query)
        # Assert
        assert len(filtered) == 0
