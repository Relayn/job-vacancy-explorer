import pytest
from unittest.mock import patch, Mock
import sqlite3
from tabulate import tabulate

# Импортируем функцию, которую будем тестировать
from parsers.view_vakancies import view_vacancies


@pytest.fixture
def mock_sqlite_connection():
    # Мокируем sqlite3.connect для изоляции тестов от реальной БД
    with patch("parsers.view_vakancies.sqlite3.connect") as mock_connect:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        yield mock_conn, mock_cursor


def test_view_vacancies_no_vacancies(mock_sqlite_connection):
    # Arrange
    mock_conn, mock_cursor = mock_sqlite_connection
    mock_cursor.fetchall.return_value = []  # Нет вакансий в БД

    with patch("builtins.print") as mock_print:
        # Act
        view_vacancies(limit=5)

        # Assert
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM vacancies LIMIT ?", (5,)
        )
        mock_print.assert_called_once_with("Нет сохраненных вакансий")
        mock_conn.close.assert_called_once()


def test_view_vacancies_with_data(mock_sqlite_connection):
    # Arrange
    mock_conn, mock_cursor = mock_sqlite_connection
    mock_vacancies_data = [
        (1, "Python Dev", "Comp1", "City1", "1000", "Desc1", "2023-01-01", "Source1"),
        (2, "Java Dev", "Comp2", "City2", "2000", "Desc2", "2023-01-02", "Source2"),
    ]
    mock_cursor.fetchall.return_value = mock_vacancies_data

    # Мокируем tabulate, чтобы проверить, что она вызывается с правильными данными
    with patch("parsers.view_vakancies.tabulate") as mock_tabulate:
        with patch("builtins.print") as mock_print:
            # Act
            view_vacancies(limit=2)

            # Assert
            mock_cursor.execute.assert_called_once_with(
                "SELECT * FROM vacancies LIMIT ?", (2,)
            )
            mock_tabulate.assert_called_once()
            # Проверяем, что tabulate вызывается с данными и заголовками
            args, kwargs = mock_tabulate.call_args
            assert args[0] == mock_vacancies_data
            assert kwargs["headers"] == [
                "ID",
                "Название",
                "Компания",
                "Локация",
                "Зарплата",
                "Описание",
                "Дата",
                "Источник",
            ]
            assert "grid" in kwargs["tablefmt"]
            mock_print.assert_called_once()  # Проверяем, что print был вызван (для вывода таблицы)
            mock_conn.close.assert_called_once()


def test_view_vacancies_db_error(mock_sqlite_connection):
    # Arrange
    mock_conn, mock_cursor = mock_sqlite_connection
    mock_cursor.execute.side_effect = sqlite3.Error("Database error")

    with patch("builtins.print") as mock_print:
        # Act
        view_vacancies(limit=10)

        # Assert
        # mock_cursor.execute.assert_called_once_with(
        #     "SELECT * FROM vacancies LIMIT ?", (10,)
        # )
        mock_print.assert_called_once_with(
            "Ошибка при получении вакансий: Database error"
        )
        mock_conn.close.assert_called_once()
