import pytest
from unittest.mock import patch, Mock
import sqlite3
import os
from datetime import datetime

# Импортируем тестируемые функции
from core.database import (
    get_db_path,
    create_connection,
    initialize_database,
    create_table,
    insert_vacancy,
    migrate_add_original_url_column,
    get_all_vacancies,
    search_vacancies,
    get_filtered_vacancies,
    get_total_vacancies_count,
    remove_duplicates,
    get_unique_sources,
    get_unique_cities,
)
from parsers.hh_parser import Vacancy  # Для тестирования insert_vacancy


@pytest.fixture
def mock_db_path():
    # This mocks os.path.abspath when it's called from core/database.py
    # It will return the full absolute path to core/database.py
    with patch(
        "core.database.os.path.abspath",
        return_value="C:\\Users\\Alex\\Documents\\GitHub\\job-vacancy-explorer\\core\\database.py",
    ) as mock_abspath:
        with patch(
            "core.database.os.path.dirname",
            return_value="C:\\Users\\Alex\\Documents\\GitHub\\job-vacancy-explorer\\core",
        ) as mock_dirname:
            with patch("core.database.os.path.join") as mock_join:
                mock_join.return_value = "C:\\Users\\Alex\\Documents\\GitHub\\job-vacancy-explorer\\parsers\\vacancies.db"
                yield mock_dirname, mock_join, mock_abspath


@pytest.fixture
def mock_sqlite_connection():
    # Мокируем sqlite3.connect для изоляции тестов от реальной БД
    with patch("sqlite3.connect") as mock_connect:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        yield mock_conn, mock_cursor, mock_connect


class TestDatabase:

    def test_get_db_path(self, mock_db_path):
        # Arrange
        mock_dirname, mock_join, mock_abspath = mock_db_path
        # Act
        path = get_db_path()

        # Assert
        assert (
            path
            == "C:\\Users\\Alex\\Documents\\GitHub\\job-vacancy-explorer\\parsers\\vacancies.db"
        )
        # Here we assert that os.path.abspath from core/database.py was called with its __file__
        mock_abspath.assert_called_once_with(
            "C:\\Users\\Alex\\Documents\\GitHub\\job-vacancy-explorer\\core\\database.py"
        )
        mock_dirname.assert_called_once_with(
            "C:\\Users\\Alex\\Documents\\GitHub\\job-vacancy-explorer\\core\\database.py"
        )
        mock_join.assert_called_once_with(
            "C:\\Users\\Alex\\Documents\\GitHub\\job-vacancy-explorer\\core",
            "..",
            "parsers",
            "vacancies.db",
        )

    def test_create_connection_success(self, mock_sqlite_connection):
        # Arrange
        mock_conn, _, mock_connect = mock_sqlite_connection
        mock_connect.return_value = mock_conn

        # Act
        conn = create_connection()

        # Assert
        assert conn == mock_conn
        mock_connect.assert_called_once_with(get_db_path())

    def test_create_connection_error(self, mock_sqlite_connection):
        # Arrange
        mock_conn, _, mock_connect = mock_sqlite_connection
        mock_connect.side_effect = sqlite3.Error("Connection error")

        with patch("builtins.print") as mock_print:
            # Act
            conn = create_connection()

            # Assert
            assert conn is None
            mock_print.assert_called_once_with(
                "Error of creating connection: Connection error"
            )
            mock_connect.assert_called_once_with(get_db_path())

    @patch("core.database.create_table")
    @patch("core.database.migrate_add_original_url_column")
    @patch("core.database.create_connection")
    def test_initialize_database_success(
        self,
        mock_create_connection,
        mock_migrate_add_original_url_column,
        mock_create_table,
    ):
        # Arrange
        mock_conn = Mock()
        mock_create_connection.return_value = mock_conn

        # Act
        initialize_database()

        # Assert
        mock_create_connection.assert_called_once()
        mock_create_table.assert_called_once_with(mock_conn)
        mock_migrate_add_original_url_column.assert_called_once_with(mock_conn)
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection", return_value=None)
    def test_initialize_database_connection_error(self, mock_create_connection):
        # Arrange
        with patch("builtins.print") as mock_print:
            # Act
            initialize_database()

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Error! cannot create the database connection."
            )

    def test_create_table(self, mock_sqlite_connection):
        # Arrange
        mock_conn, mock_cursor, _ = mock_sqlite_connection

        # Act
        create_table(mock_conn)

        # Assert
        mock_cursor.execute.assert_called_once()
        assert (
            "CREATE TABLE IF NOT EXISTS vacancies"
            in mock_cursor.execute.call_args[0][0]
        )
        mock_conn.commit.assert_called_once()

    def test_create_table_error(self, mock_sqlite_connection):
        # Arrange
        mock_conn, mock_cursor, _ = mock_sqlite_connection
        mock_cursor.execute.side_effect = sqlite3.Error("Table creation error")

        with patch("builtins.print") as mock_print:
            # Act
            create_table(mock_conn)

            # Assert
            mock_print.assert_called_once_with(
                "Error of creating table: Table creation error"
            )
            mock_conn.commit.assert_not_called()

    def test_migrate_add_original_url_column_adds_column(self, mock_sqlite_connection):
        # Arrange
        mock_conn, mock_cursor, _ = mock_sqlite_connection
        # Имитируем отсутствие столбца original_url
        mock_cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "title", "TEXT", 1, None, 0),
        ]  # Corrected mock return value format for PRAGMA table_info

        with patch("builtins.print") as mock_print:
            # Act
            migrate_add_original_url_column(mock_conn)

            # Assert
            mock_cursor.execute.assert_any_call("PRAGMA table_info(vacancies)")
            mock_cursor.execute.assert_any_call(
                "ALTER TABLE vacancies ADD COLUMN original_url TEXT NOT NULL DEFAULT ''"
            )
            mock_conn.commit.assert_called_once()
            mock_print.assert_called_once_with("Столбец original_url успешно добавлен.")

    def test_migrate_add_original_url_column_column_exists(
        self, mock_sqlite_connection
    ):
        # Arrange
        mock_conn, mock_cursor, _ = mock_sqlite_connection
        # Имитируем наличие столбца original_url
        mock_cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "title", "TEXT", 1, None, 0),
            (2, "original_url", "TEXT", 1, None, 0),
        ]  # Corrected mock return value format

        with patch("builtins.print") as mock_print:
            # Act
            migrate_add_original_url_column(mock_conn)

            # Assert
            mock_cursor.execute.assert_called_once_with("PRAGMA table_info(vacancies)")
            mock_cursor.execute.call_count == 1  # Только PRAGMA запрос
            mock_conn.commit.assert_not_called()  # Изменений не было
            mock_print.assert_not_called()  # Сообщение не должно выводиться

    def test_migrate_add_original_url_column_error(self, mock_sqlite_connection):
        # Arrange
        mock_conn, mock_cursor, _ = mock_sqlite_connection
        mock_cursor.execute.side_effect = sqlite3.Error("Migration error")

        with patch("builtins.print") as mock_print:
            # Act
            migrate_add_original_url_column(mock_conn)

            # Assert
            mock_print.assert_called_once_with(
                "Ошибка миграции original_url: Migration error"
            )
            mock_conn.commit.assert_not_called()

    @patch("core.database.create_connection")
    def test_insert_vacancy_success(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        vacancy = Vacancy(
            title="Test Vacancy",
            company="Test Company",
            location="Test Location",
            salary="1000 USD",
            description="Test Description",
            published_at=datetime(2023, 1, 1),
            source="Test Source",
            original_url="http://example.com/vacancy/1",
        )

        # Act
        insert_vacancy(vacancy)

        # Assert
        mock_create_connection.assert_called_once()
        mock_cursor.execute.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        sql_query = args[0]
        params = args[1]

        assert "INSERT OR IGNORE INTO vacancies" in sql_query
        assert params[0] == vacancy.title
        assert params[1] == vacancy.company
        assert params[2] == vacancy.location
        assert params[3] == vacancy.salary
        assert params[4] == vacancy.description
        assert params[5] == vacancy.published_at.isoformat()
        assert params[6] == vacancy.source
        assert params[7] == vacancy.original_url
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_insert_vacancy_with_relative_url(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        vacancy = Vacancy(
            title="Test Vacancy",
            company="Test Company",
            location="Test Location",
            salary="1000 USD",
            description="Test Description",
            published_at=datetime(2023, 1, 1),
            source="Test Source",
            original_url="example.com/vacancy/1",  # Relative URL
        )

        # Act
        insert_vacancy(vacancy)

        # Assert
        mock_create_connection.assert_called_once()
        mock_cursor.execute.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        params = args[1]

        assert (
            params[7] == "https://example.com/vacancy/1"
        )  # Should be converted to absolute URL
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_insert_vacancy_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Insert error")

        vacancy = Vacancy(
            title="Test Vacancy",
            company="Test Company",
            location="Test Location",
            salary="1000 USD",
            description="Test Description",
            published_at=datetime(2023, 1, 1),
            source="Test Source",
            original_url="http://example.com/vacancy/1",
        )

        with patch("builtins.print") as mock_print:
            # Act
            insert_vacancy(vacancy)

            # Assert
            mock_create_connection.assert_called_once()
            mock_cursor.execute.assert_called_once()
            mock_print.assert_called_once_with(
                "Error of inserting vacancy: Insert error"
            )
            mock_conn.commit.assert_not_called()  # Should not commit on error
            mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_all_vacancies_success(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            (
                1,
                "Title1",
                "Comp1",
                "Loc1",
                "100",
                "Desc1",
                "2023-01-01",
                "Source1",
                "url1",
            ),
            (
                2,
                "Title2",
                "Comp2",
                "Loc2",
                "200",
                "Desc2",
                "2023-01-02",
                "Source2",
                "url2",
            ),
        ]

        # Act
        vacancies = get_all_vacancies(
            page=1, per_page=2, order_by="id", order_direction="ASC"
        )

        # Assert
        mock_create_connection.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM vacancies ORDER BY id ASC LIMIT ? OFFSET ?", (2, 0)
        )
        assert len(vacancies) == 2
        assert vacancies[0]["title"] == "Title1"
        assert vacancies[1]["original_url"] == "url2"
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_all_vacancies_no_data(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = []

        # Act
        vacancies = get_all_vacancies()

        # Assert
        mock_create_connection.assert_called_once()
        assert len(vacancies) == 0
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_all_vacancies_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("DB error")

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = get_all_vacancies()

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Error of getting all vacancies: DB error"
            )
            assert len(vacancies) == 0
            mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_search_vacancies_success(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            (
                1,
                "Python Dev",
                "Comp1",
                "Loc1",
                "100",
                "Desc1",
                "2023-01-01",
                "Source1",
                "url1",
            ),
        ]

        # Act
        vacancies = search_vacancies("Python")

        # Assert
        mock_create_connection.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM vacancies WHERE title LIKE ? OR company LIKE ? OR location LIKE ?",
            ("%Python%", "%Python%", "%Python%"),
        )
        assert len(vacancies) == 1
        assert vacancies[0]["title"] == "Python Dev"
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_search_vacancies_no_results(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        # Act
        vacancies = search_vacancies("NonExistent")

        # Assert
        mock_create_connection.assert_called_once()
        assert len(vacancies) == 0
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_search_vacancies_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Search error")

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = search_vacancies("Python")

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Error of searching vacancies: Search error"
            )
            assert len(vacancies) == 0
            mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_filtered_vacancies_all_filters(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            (
                1,
                "Python Dev",
                "Comp1",
                "Loc1",
                "100",
                "Desc1",
                "2023-01-01",
                "Source1",
                "url1",
            ),
        ]

        # Act
        vacancies = get_filtered_vacancies(
            query="Python",
            location="Loc1",
            company="Comp1",
            page=1,
            per_page=10,
            order_by="id",
        )

        # Assert
        mock_create_connection.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        sql_query = args[0]
        params = args[1]

        # Modified assertion to be less strict about whitespace
        assert (
            "SELECT id, title, company, location, salary, description, published_at, source, original_url FROM vacancies"
            in sql_query
        )
        assert "WHERE" in sql_query
        assert "title LIKE ?" in sql_query
        assert "company LIKE ?" in sql_query
        assert "location LIKE ?" in sql_query
        assert "%Python%" in params
        assert "%Loc1%" in params
        assert "%Comp1%" in params
        assert "ORDER BY id DESC LIMIT ? OFFSET ?" in sql_query
        assert (10, 0) == tuple(params[-2:])  # Check limit and offset parameters
        assert len(vacancies) == 1
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_filtered_vacancies_no_filters(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (
                1,
                "Python Dev",
                "Comp1",
                "Loc1",
                "100",
                "Desc1",
                "2023-01-01",
                "Source1",
                "url1",
            ),
        ]

        # Act
        vacancies = get_filtered_vacancies()

        # Assert
        mock_create_connection.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        sql_query = args[0]

        # Modified assertion to be less strict about whitespace
        assert (
            "SELECT id, title, company, location, salary, description, published_at, source, original_url FROM vacancies"
            in sql_query
        )
        assert (
            "WHERE 1=1" in sql_query
        )  # Even with no filters, the base query includes WHERE 1=1
        assert "ORDER BY id DESC LIMIT ? OFFSET ?" in sql_query
        assert (50, 0) == tuple(args[1])  # Default limit and offset parameters
        assert len(vacancies) == 1
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_filtered_vacancies_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Filter error")

        with patch("builtins.print") as mock_print:
            # Act
            vacancies = get_filtered_vacancies(query="test")

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Error of getting filtered vacancies: Filter error"
            )
            assert len(vacancies) == 0
            mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_total_vacancies_count_with_filters(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (5,)

        # Act
        count = get_total_vacancies_count(
            query="Python", location="Moscow", company="Test"
        )

        # Assert
        mock_create_connection.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        sql_query = args[0]
        params = args[1]

        assert "SELECT COUNT(*) FROM vacancies" in sql_query
        assert "WHERE" in sql_query
        assert "title LIKE ?" in sql_query
        assert "company LIKE ?" in sql_query
        assert "location LIKE ?" in sql_query
        assert "%Python%" in params
        assert "%Moscow%" in params
        assert "%Test%" in params
        assert count == 5
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_total_vacancies_count_no_filters(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (100,)

        # Act
        count = get_total_vacancies_count()

        # Assert
        mock_create_connection.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        sql_query = args[0]

        assert "SELECT COUNT(*) FROM vacancies" in sql_query
        assert (
            "WHERE 1=1" in sql_query
        )  # Even with no filters, the base query includes WHERE 1=1
        assert count == 100
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_total_vacancies_count_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Count error")

        with patch("builtins.print") as mock_print:
            # Act
            count = get_total_vacancies_count()

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Error getting total vacancies count: Count error"
            )
            assert count == 0
            mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_remove_duplicates_success(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        with patch("builtins.print") as mock_print:
            # Act
            remove_duplicates()

            # Assert
            mock_create_connection.assert_called_once()
            mock_cursor.execute.assert_called_once()
            # Use .strip() and 'in' for more robust assertion against whitespace
            expected_sql = "DELETE FROM vacancies WHERE id NOT IN ( SELECT MIN(id) FROM vacancies GROUP BY title, company, published_at );"
            actual_sql_raw = mock_cursor.execute.call_args[0][0]
            actual_sql_clean = " ".join(actual_sql_raw.split()).strip()
            assert expected_sql.replace("\n", " ").strip() == actual_sql_clean
            mock_print.assert_called_once_with("Дубликаты удалены успешно.")

    @patch("core.database.create_connection")
    def test_remove_duplicates_connection_error(self, mock_create_connection):
        # Arrange
        mock_create_connection.return_value = None

        with patch("builtins.print") as mock_print:
            # Act
            remove_duplicates()

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Ошибка: не удалось подключиться к базе данных."
            )

    @patch("core.database.create_connection")
    def test_remove_duplicates_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Delete error")

        with patch("builtins.print") as mock_print:
            # Act
            remove_duplicates()

            # Assert
            mock_create_connection.assert_called_once()
            mock_cursor.execute.assert_called_once()
            mock_print.assert_called_once_with(
                "Ошибка при удалении дубликатов: Delete error"
            )
            mock_conn.commit.assert_not_called()
            mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_unique_sources_success(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("Source1",), ("Source2",)]

        # Act
        sources = get_unique_sources()

        # Assert
        mock_create_connection.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "SELECT DISTINCT source FROM vacancies"
        )
        assert sources == ["Source1", "Source2"]
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_unique_sources_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Sources error")

        with patch("builtins.print") as mock_print:
            # Act
            sources = get_unique_sources()

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Error getting unique sources: Sources error"
            )
            assert sources == []
            mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_unique_cities_success(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("City1",), ("City2",)]

        # Act
        cities = get_unique_cities()

        # Assert
        mock_create_connection.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "SELECT DISTINCT location FROM vacancies"
        )
        assert cities == ["City1", "City2"]
        mock_conn.close.assert_called_once()

    @patch("core.database.create_connection")
    def test_get_unique_cities_db_error(self, mock_create_connection):
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Cities error")

        with patch("builtins.print") as mock_print:
            # Act
            cities = get_unique_cities()

            # Assert
            mock_create_connection.assert_called_once()
            mock_print.assert_called_once_with(
                "Error getting unique cities: Cities error"
            )
            assert cities == []
            mock_conn.close.assert_called_once()
