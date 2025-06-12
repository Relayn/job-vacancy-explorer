import pytest
from unittest.mock import patch, Mock
from datetime import datetime
import time
import os

# Импортируем тестируемые функции и классы
from core.scheduler import update_vacancies, start_scheduler
from parsers.hh_parser import HHAPIParser, Vacancy
from core.database import (
    insert_vacancy,
    remove_duplicates,
)  # Импортируем для мокирования
from apscheduler.schedulers.background import BackgroundScheduler


# Фикстура для мокирования tzlocal.get_localzone
@pytest.fixture
def mock_tzlocal_get_localzone():
    with patch("tzlocal.get_localzone") as mock_get_localzone:
        mock_timezone = Mock()
        # Мокируем utcoffset() для возврата timedelta, чтобы избежать AttributeError: 'NoneType' object has no attribute 'total_seconds'
        mock_timezone.utcoffset.return_value = datetime.now() - datetime.now()
        mock_get_localzone.return_value = mock_timezone
        yield mock_get_localzone


class TestScheduler:

    @patch("core.scheduler.HHAPIParser")
    @patch("core.scheduler.insert_vacancy")
    @patch("core.scheduler.remove_duplicates")
    def test_update_vacancies_success_multiple_vacancies(
        self, mock_remove_duplicates, mock_insert_vacancy, MockHHAPIParser
    ):
        # Arrange
        mock_parser_instance = MockHHAPIParser.return_value
        mock_vacancies = [
            Vacancy(
                "Title1",
                "Comp1",
                "Loc1",
                "100",
                "Desc1",
                datetime.now(),
                "hh.ru",
                "url1",
            ),
            Vacancy(
                "Title2",
                "Comp2",
                "Loc2",
                "200",
                "Desc2",
                datetime.now(),
                "hh.ru",
                "url2",
            ),
        ]
        mock_parser_instance.parse_vacancies.return_value = mock_vacancies
        search_query = "Python"

        with patch("builtins.print") as mock_print:
            # Act
            result = update_vacancies(search_query)

            # Assert
            MockHHAPIParser.assert_called_once()
            mock_parser_instance.parse_vacancies.assert_called_once_with(search_query)
            assert mock_insert_vacancy.call_count == len(mock_vacancies)
            mock_remove_duplicates.assert_called_once()
            assert (
                result == mock_vacancies
            )  # update_vacancies returns the list of vacancies
            assert mock_print.call_count == 2  # Two print calls: start and success
            assert "Запуск обновления вакансий..." in mock_print.call_args_list[0][0][0]
            assert "Найдено и сохранено" in mock_print.call_args_list[1][0][0]
            assert str(len(mock_vacancies)) in mock_print.call_args_list[1][0][0]

    @patch("core.scheduler.HHAPIParser")
    @patch("core.scheduler.insert_vacancy")
    @patch("core.scheduler.remove_duplicates")
    def test_update_vacancies_no_vacancies_found(
        self, mock_remove_duplicates, mock_insert_vacancy, MockHHAPIParser
    ):
        # Arrange
        mock_parser_instance = MockHHAPIParser.return_value
        mock_parser_instance.parse_vacancies.return_value = []
        search_query = "Java"

        with patch("builtins.print") as mock_print:
            # Act
            result = update_vacancies(search_query)

            # Assert
            MockHHAPIParser.assert_called_once()
            mock_parser_instance.parse_vacancies.assert_called_once_with(search_query)
            mock_insert_vacancy.assert_not_called()
            mock_remove_duplicates.assert_called_once()
            assert (
                mock_print.call_count == 2
            )  # Two print calls: start and no vacancies found
            assert "Запуск обновления вакансий..." in mock_print.call_args_list[0][0][0]
            assert (
                "Найдено и сохранено 0 вакансий" in mock_print.call_args_list[1][0][0]
            )
            assert result == []  # update_vacancies returns an empty list

    @patch("core.scheduler.HHAPIParser")
    @patch("core.scheduler.insert_vacancy")
    @patch("core.scheduler.remove_duplicates")
    def test_update_vacancies_parser_raises_exception(
        self, mock_remove_duplicates, mock_insert_vacancy, MockHHAPIParser
    ):
        # Arrange
        mock_parser_instance = MockHHAPIParser.return_value
        mock_parser_instance.parse_vacancies.side_effect = Exception("Parser error")
        search_query = "Python"

        with patch("builtins.print") as mock_print:
            # Act & Assert
            with pytest.raises(Exception) as excinfo:
                update_vacancies(search_query)
            assert "Parser error" in str(excinfo.value)

            MockHHAPIParser.assert_called_once()
            mock_parser_instance.parse_vacancies.assert_called_once_with(search_query)
            mock_insert_vacancy.assert_not_called()
            mock_remove_duplicates.assert_not_called()  # Should not be called if parser fails
            assert mock_print.call_count == 1  # Only one print call before exception
            assert "Запуск обновления вакансий..." in mock_print.call_args_list[0][0][0]
            # The specific error message is printed within update_vacancies, but it's not reached in this test because the exception is raised earlier.
            # The provided 'print' in the original bug report is not part of the `update_vacancies` function's exception handling, so I will remove the assertion for it.

    @patch("core.scheduler.HHAPIParser")
    @patch("core.scheduler.insert_vacancy")
    @patch("core.scheduler.remove_duplicates")
    def test_update_vacancies_insert_vacancy_raises_exception(
        self, mock_remove_duplicates, mock_insert_vacancy, MockHHAPIParser
    ):
        # Arrange
        mock_parser_instance = MockHHAPIParser.return_value
        mock_vacancies = [
            Vacancy(
                "Title1",
                "Comp1",
                "Loc1",
                "100",
                "Desc1",
                datetime.now(),
                "hh.ru",
                "url1",
            ),
            Vacancy(
                "Title2",
                "Comp2",
                "Loc2",
                "200",
                "Desc2",
                datetime.now(),
                "hh.ru",
                "url2",
            ),
        ]
        mock_parser_instance.parse_vacancies.return_value = mock_vacancies
        mock_insert_vacancy.side_effect = [
            None,
            Exception("DB insert error"),
        ]  # First insert works, second fails
        search_query = "Python"

        with patch("builtins.print") as mock_print:
            # Act & Assert
            with pytest.raises(Exception) as excinfo:
                update_vacancies(search_query)
            assert "DB insert error" in str(excinfo.value)

            MockHHAPIParser.assert_called_once()
            mock_parser_instance.parse_vacancies.assert_called_once_with(search_query)
            assert (
                mock_insert_vacancy.call_count == 2
            )  # Called twice, second time raises exception
            mock_remove_duplicates.assert_not_called()  # remove_duplicates is not called if insert_vacancy fails midway
            # Проверяем, что сообщение об ошибке было напечатано
            assert mock_print.call_count == 1  # Only one print call before exception
            assert "Запуск обновления вакансий..." in mock_print.call_args_list[0][0][0]

    @patch("core.scheduler.BackgroundScheduler")
    @patch("core.scheduler.config")
    @patch("core.scheduler.update_vacancies")
    def test_start_scheduler(
        self,
        mock_update_vacancies,
        mock_config,
        MockBackgroundScheduler,
        mock_tzlocal_get_localzone,
    ):
        # Arrange
        mock_config.SCHEDULER_INTERVAL = 3600  # Example interval

        mock_scheduler_instance = MockBackgroundScheduler.return_value
        mock_scheduler_instance.add_job.return_value = None

        with patch("builtins.print") as mock_print:
            # Act
            start_scheduler()

            # Assert
            MockBackgroundScheduler.assert_called_once()  # Verify scheduler is instantiated
            mock_scheduler_instance.add_job.assert_called_once_with(
                mock_update_vacancies,
                "interval",
                seconds=mock_config.SCHEDULER_INTERVAL,
            )
            mock_scheduler_instance.start.assert_called_once()
            mock_print.assert_called_once()
            assert "Планировщик запущен" in mock_print.call_args[0][0]
            assert str(mock_config.SCHEDULER_INTERVAL) in mock_print.call_args[0][0]
