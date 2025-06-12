import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import requests
import sqlite3

# Предполагается, что Vacancy dataclass и HHAPIParser класс находятся в parsers.hh_parser
from parsers.hh_parser import HHAPIParser, Vacancy


# Мок-ответы для успешных вызовов API
MOCK_API_RESPONSE_PAGE1 = {
    "items": [
        {
            "id": "1",
            "name": "Python Developer",
            "employer": {"name": "Test Company 1"},
            "area": {"name": "Moscow"},
            "salary": {"from": 100000, "to": 150000, "currency": "RUR"},
            "snippet": {
                "requirement": "Experience with Python",
                "responsibility": "Develop backend",
            },
            "published_at": "2023-01-01T10:00:00+0300",
            "alternate_url": "https://hh.ru/vacancy/1",
        },
        {
            "id": "2",
            "name": "Data Scientist",
            "employer": {"name": "Test Company 2"},
            "area": {"name": "Saint Petersburg"},
            "salary": None,
            "snippet": {"responsibility": "Analyze data"},
            "published_at": "2023-01-02T11:00:00+0300",
            "alternate_url": "https://hh.ru/vacancy/2",
        },
    ],
    "pages": 2,
    "page": 0,
}

MOCK_API_RESPONSE_PAGE2 = {
    "items": [
        {
            "id": "3",
            "name": "Junior Python Dev",
            "employer": {"name": "Test Company 3"},
            "area": {"name": "Novosibirsk"},
            "salary": {"from": 50000, "currency": "RUR"},
            "snippet": {"requirement": "Basic Python knowledge"},
            "published_at": "2023-01-03T12:00:00+0300",
            "alternate_url": "https://hh.ru/vacancy/3",
        }
    ],
    "pages": 2,
    "page": 1,
}

MOCK_API_RESPONSE_EMPTY = {"items": [], "pages": 1, "page": 0}


class TestHHAPIParser:
    @pytest.fixture
    def parser(self):
        # Patch sqlite3.connect for the database connection
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Patch _create_table to prevent actual table creation during tests
            with patch.object(HHAPIParser, "_create_table"):
                # Patch requests.Session in the module where HHAPIParser uses it
                with patch("parsers.hh_parser.requests.Session") as MockRequestsSession:
                    # Configure the mock session instance that HHAPIParser will use
                    mock_session_instance = Mock()
                    MockRequestsSession.return_value = mock_session_instance

                    parser = HHAPIParser()  # HHAPIParser will now get the mock session

                    yield parser

                    # Ensure connections are closed
                    if hasattr(parser, "conn") and parser.conn:
                        parser.conn.close()

    @patch("sqlite3.connect")
    def test_init(self, mock_sqlite_connect):
        # Arrange & Act
        with patch.object(HHAPIParser, "_create_table") as mock_create_table_init:
            # Patch requests.Session specifically for this test's HHAPIParser instantiation
            with patch(
                "parsers.hh_parser.requests.Session"
            ) as MockRequestsSessionForInit:
                parser = HHAPIParser()

        # Assert
        MockRequestsSessionForInit.assert_called_once()
        assert isinstance(parser.session, Mock)
        assert parser.conn is not None
        assert parser.cursor is not None
        mock_sqlite_connect.assert_called_once_with(
            "vacancies.db", check_same_thread=False
        )
        mock_create_table_init.assert_called_once()
        parser.conn.close()  # Cleanup for this specific test

    def test_create_table(self, parser):
        # Arrange
        # _create_table is mocked in the fixture, so we need to call it explicitly
        # to assert its behavior.
        parser._create_table()

        # Assert
        parser.cursor.execute.assert_called_once()

    @pytest.mark.parametrize(
        "salary_data, expected",
        [
            (None, None),
            ({}, None),
            ({"from": 1000, "currency": "USD"}, "от 1000 USD"),
            ({"to": 2000, "currency": "EUR"}, "до 2000 EUR"),
            ({"from": 1000, "to": 2000, "currency": "RUR"}, "от 1000 до 2000 RUR"),
            ({"from": 50000}, "от 50000 RUR"),  # Валюта по умолчанию
        ],
    )
    def test_parse_salary(self, parser, salary_data, expected):
        # Arrange & Act
        result = parser._parse_salary(salary_data)

        # Assert
        assert result == expected

    @pytest.mark.parametrize(
        "snippet_data, expected",
        [
            ({"requirement": "Req", "responsibility": "Resp"}, "Req Resp"),
            ({"requirement": "Req"}, "Req"),
            ({"responsibility": "Resp"}, "Resp"),
            ({}, ""),
            ({"requirement": None, "responsibility": None}, ""),
            ({"requirement": "", "responsibility": ""}, ""),
        ],
    )
    def test_get_vacancy_description(self, parser, snippet_data, expected):
        # Arrange & Act
        item = {"snippet": snippet_data}
        result = parser._get_vacancy_description(item)

        # Assert
        assert result == expected

    def test_save_vacancy_success(self, parser):
        # Arrange
        vacancy = Vacancy(
            title="Test Vacancy",
            company="Test Co",
            location="Test City",
            salary="1000 RUR",
            description="Test Desc",
            published_at=datetime.now(timezone.utc),
            source="test.com",
            original_url="http://test.com",
        )

        # Act
        parser._save_vacancy(vacancy)

        # Assert
        parser.cursor.execute.assert_called_once()
        parser.conn.commit.assert_called_once()

    def test_save_vacancy_duplicate(self, parser):
        # Arrange
        parser.cursor.execute.side_effect = sqlite3.IntegrityError("Duplicate entry")
        vacancy = Vacancy(
            title="Test Vacancy",
            company="Test Co",
            location="Test City",
            salary="1000 RUR",
            description="Test Desc",
            published_at=datetime.now(timezone.utc),
            source="test.com",
            original_url="http://test.com",
        )
        with patch("builtins.print") as mock_print:
            # Act
            parser._save_vacancy(vacancy)

            # Assert
            mock_print.assert_called_with("Ошибка сохранения в БД: Duplicate entry")
            parser.conn.commit.assert_not_called()  # Коммит не должен происходить при ошибке

    def test_save_vacancy_other_db_error(self, parser):
        # Arrange
        parser.cursor.execute.side_effect = sqlite3.Error("Some DB error")
        vacancy = Vacancy(
            title="Test Vacancy",
            company="Test Co",
            location="Test City",
            salary="1000 RUR",
            description="Test Desc",
            published_at=datetime.now(timezone.utc),
            source="test.com",
            original_url="http://test.com",
        )
        with patch("builtins.print") as mock_print:
            # Act
            parser._save_vacancy(vacancy)

            # Assert
            mock_print.assert_called_with("Ошибка сохранения в БД: Some DB error")
            parser.conn.commit.assert_not_called()

    @patch("time.sleep", return_value=None)
    def test_parse_vacancies_success_multiple_pages(self, mock_sleep, parser):
        # Arrange
        mock_response1 = Mock()
        mock_response1.json.return_value = MOCK_API_RESPONSE_PAGE1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = MOCK_API_RESPONSE_PAGE2
        mock_response2.raise_for_status.return_value = None

        # Мокируем session.get, чтобы возвращать разные ответы для разных страниц
        parser.session.get.side_effect = [mock_response1, mock_response2]
        parser._save_vacancy = (
            Mock()
        )  # Мокируем save_vacancy, чтобы избежать реальных вызовов БД

        # Act
        vacancies = parser.parse_vacancies("Python")

        # Assert
        assert len(vacancies) == 3
        assert parser.session.get.call_count == 2
        assert parser._save_vacancy.call_count == 3

        # Проверяем разобранные данные
        assert vacancies[0].title == "Python Developer"
        assert vacancies[1].title == "Data Scientist"
        assert vacancies[2].title == "Junior Python Dev"

        # Проверяем логику пагинации
        assert parser.session.get.call_args_list[0].kwargs["params"]["page"] == 0
        assert parser.session.get.call_args_list[1].kwargs["params"]["page"] == 1

    @patch("time.sleep", return_value=None)
    def test_parse_vacancies_api_error(self, mock_sleep, parser):
        # Arrange
        parser.session.get.side_effect = requests.RequestException("API down")
        parser._save_vacancy = Mock()  # Mock save_vacancy

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = parser.parse_vacancies("Python")

            # Assert
            assert len(vacancies) == 0
            mock_print.assert_called_with("Ошибка запроса: API down")
            parser._save_vacancy.assert_not_called()

    @patch("time.sleep", return_value=None)
    def test_parse_vacancies_empty_data(self, mock_sleep, parser):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = MOCK_API_RESPONSE_EMPTY
        mock_response.raise_for_status.return_value = None
        parser.session.get.return_value = mock_response
        parser._save_vacancy = Mock()  # Mock save_vacancy

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = parser.parse_vacancies("Python")

            # Assert
            assert len(vacancies) == 0
            mock_print.assert_not_called()  # No error should be printed
            parser._save_vacancy.assert_not_called()

    @patch("time.sleep", return_value=None)
    def test_parse_vacancies_data_parsing_error(self, mock_sleep, parser):
        # Arrange
        malformed_response = {
            "items": [
                {
                    "id": "1",
                    "name": "Valid Vacancy",
                    "employer": {"name": "Company"},
                    "area": {"name": "City"},
                    "published_at": "2023-01-01T10:00:00+0300",
                    # Отсутствует salary и snippet, но также делается недействительный формат published_at для следующего теста
                },
                {
                    "id": "2",
                    "name": "Invalid Date",
                    "employer": {"name": "Company"},
                    "area": {"name": "City"},
                    "published_at": "INVALID_DATE",  # Намеренно неверная дата
                },
            ],
            "pages": 1,
            "page": 0,
        }
        mock_response = Mock()
        mock_response.json.return_value = malformed_response
        mock_response.raise_for_status.return_value = None
        parser.session.get.return_value = mock_response
        parser._save_vacancy = Mock()  # Mock save_vacancy

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = parser.parse_vacancies("Python")

            # Assert
            assert len(vacancies) == 1  # Only the valid vacancy should be parsed
            assert vacancies[0].title == "Valid Vacancy"
            # Check that the error message for the invalid date is printed
            mock_print.assert_called_with(
                "Пропущена вакансия из-за ошибки в данных: time data 'INVALID_DATE' does not match format '%Y-%m-%dT%H:%M:%S%z'"
            )
            parser._save_vacancy.assert_called_once()  # Only the valid vacancy should be saved

    @patch("time.sleep", return_value=None)
    def test_parse_vacancies_key_error_in_item(self, mock_sleep, parser):
        # Arrange
        malformed_response = {
            "items": [
                {
                    "id": "1",
                    "name": "Valid Vacancy",
                    "employer": {"name": "Company"},
                    "area": {"name": "City"},
                    "published_at": "2023-01-01T10:00:00+0300",
                },
                {
                    "id": "2",
                    "name": "Missing Employer",
                    # "employer": {"name": "Company"}, # Отсутствует ключ employer
                    "area": {"name": "City"},
                    "published_at": "2023-01-02T10:00:00+0300",
                },
            ],
            "pages": 1,
            "page": 0,
        }
        mock_response = Mock()
        mock_response.json.return_value = malformed_response
        mock_response.raise_for_status.return_value = None
        parser.session.get.return_value = mock_response
        parser._save_vacancy = Mock()  # Mock save_vacancy

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = parser.parse_vacancies("Python")

            # Assert
            assert len(vacancies) == 1  # Only the valid vacancy should be parsed
            assert vacancies[0].title == "Valid Vacancy"
            # Check that the error message for the missing key is printed
            mock_print.assert_called_with(
                "Пропущена вакансия из-за ошибки в данных: 'employer'"
            )
            parser._save_vacancy.assert_called_once()  # Only the valid vacancy should be saved

    @patch("time.sleep", return_value=None)
    def test_parse_vacancies_exception_handling(self, mock_sleep, parser):
        # Arrange
        parser.session.get.side_effect = Exception("Unexpected error")
        parser._save_vacancy = Mock()  # Mock save_vacancy

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = parser.parse_vacancies("Python")

            # Assert
            assert len(vacancies) == 0
            mock_print.assert_called_with(
                "Критическая ошибка парсинга: Unexpected error"
            )
            parser._save_vacancy.assert_not_called()

    def test_del_closes_session_and_conn(self):
        # Arrange
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            with patch.object(HHAPIParser, "_create_table"):
                with patch("parsers.hh_parser.requests.Session") as MockHHParserSession:
                    parser = HHAPIParser()
                    parser.session = (
                        Mock()
                    )  # Ensure parser.session is a mock for this test
                    parser.conn = Mock()  # Ensure parser.conn is a mock for this test

                    # Act
                    # Assert before del to avoid UnboundLocalError
                    # Verify that close was called on the mock objects
                    # Need to explicitly call __del__ as Python's GC is unpredictable
                    parser.__del__()

                    # Assert
                    parser.session.close.assert_called_once()  # Verify that session.close was called on the mock object
                    parser.conn.close.assert_called_once()  # Verify that conn.close was called on the mock object

    def test_del_handles_missing_attributes(self):
        # Arrange
        # Используем отдельную фикстуру для этого теста, чтобы моки не мешали
        parser = HHAPIParser()
        # Имитируем, что session и conn не были установлены (например, из-за ошибки в __init__)
        if hasattr(parser, "session"):
            del parser.session
        if hasattr(parser, "conn"):
            del parser.conn

        # Act & Assert (проверяем, что нет ошибок при удалении)
        del parser
