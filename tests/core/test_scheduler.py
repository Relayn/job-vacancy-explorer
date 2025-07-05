from datetime import datetime
from unittest.mock import Mock, patch

from parsers.dto import VacancyDTO
from core.scheduler import update_vacancies


@patch("core.scheduler.get_db")
@patch("core.scheduler.add_vacancies_from_dto")
@patch("core.scheduler.SuperJobParser")
@patch("core.scheduler.HHParser")
def test_update_vacancies_success(
    MockHHParser, MockSuperJobParser, mock_add_vacancies, mock_get_db
):
    """
    Тест успешного выполнения задачи обновления вакансий.
    """
    # 1. Настраиваем мок парсера
    mock_parser_instance = MockHHParser.return_value
    mock_dto_list = [
        VacancyDTO(
            title="Test Vacancy",
            company="Test Co",
            location="Test City",
            salary="100-200",
            description="Desc",
            published_at=datetime.now(),
            source="hh.ru",
            original_url="http://test.com/1",
            salary_min_rub=100,
            salary_max_rub=200,
        )
    ]
    mock_parser_instance.parse.return_value = mock_dto_list

    # Настраиваем мок для SuperJobParser, чтобы он возвращал пустой список
    mock_superjob_instance = MockSuperJobParser.return_value
    mock_superjob_instance.parse.return_value = []

    # 2. Настраиваем мок функции добавления в БД
    mock_add_vacancies.return_value = len(mock_dto_list)

    # 3. Настраиваем мок контекстного менеджера get_db
    mock_db_session = Mock()
    mock_get_db.return_value.__enter__.return_value = mock_db_session

    # Act
    update_vacancies(search_query="Python")

    # Assert
    # Проверяем, что парсер был создан и вызван
    MockHHParser.assert_called_once()
    mock_parser_instance.parse.assert_called_once_with("Python")

    # Проверяем, что была запрошена сессия БД
    mock_get_db.assert_called_once()

    # Проверяем, что функция сохранения была вызвана с правильными данными
    mock_add_vacancies.assert_called_once_with(mock_db_session, mock_dto_list)


@patch("core.scheduler.get_db")
@patch("core.scheduler.add_vacancies_from_dto")
@patch("core.scheduler.SuperJobParser")
@patch("core.scheduler.HHParser")
def test_update_vacancies_no_vacancies_found(
    MockHHParser,
    MockSuperJobParser,
    mock_add_vacancies,
    mock_get_db,
    setup_test_db,
):
    """
    Тест сценария, когда парсер не нашел ни одной вакансии.
    """
    # Парсеры возвращают пустые списки
    MockHHParser.return_value.parse.return_value = []
    MockSuperJobParser.return_value.parse.return_value = []

    # Act
    update_vacancies(search_query="ExoticLanguage")

    # Assert
    # Парсеры были вызваны
    MockHHParser.return_value.parse.assert_called_once_with("ExoticLanguage")
    MockSuperJobParser.return_value.parse.assert_called_once_with("ExoticLanguage")

    # А вот функции для работы с БД - нет, так как список вакансий пуст
    mock_get_db.assert_not_called()
    mock_add_vacancies.assert_not_called()
