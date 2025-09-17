"""Unit tests for the Flask application routes."""

from unittest.mock import patch

from flask.testing import FlaskClient


def test_index_route(
    client: FlaskClient,
) -> None:
    """Test the index route ('/').

    Checks if the main page loads correctly and displays statistics.
    """
    # Arrange: Мокируем функции, обращающиеся к БД
    with (
        patch("app.routes.get_total_vacancies_count", return_value=123),
        patch("app.routes.get_unique_sources", return_value=["hh.ru", "superjob.ru"]),
        patch("app.routes.get_unique_cities", return_value=["Москва", "Казань"]),
    ):
        # Act: Выполняем GET-запрос к главной странице
        response = client.get("/")

        # Assert: Проверяем, что страница загрузилась успешно
        assert response.status_code == 200
        # Проверяем, что на странице отображается статистика из наших моков
        assert b"123" in response.data
        assert b"2" in response.data  # 2 источника
        assert b"2" in response.data  # 2 города


def test_vacancies_route_success(
    client: FlaskClient,
) -> None:
    """Test the vacancies route ('/vacancies') for a successful response.

    Ensures the page loads and displays vacancy information correctly.
    """
    # Arrange: Мокируем все функции, которые вызывает эндпоинт
    with (
        patch("app.routes.get_filtered_vacancies", return_value=[]),
        patch("app.routes.get_total_vacancies_count", return_value=0),
        patch("app.routes.get_unique_sources", return_value=[]),
    ):
        # Act: Выполняем GET-запрос к странице вакансий
        response = client.get("/vacancies")

        # Assert: Проверяем успешный статус и наличие ключевых элементов
        assert response.status_code == 200
        # ПРАВИЛЬНЫЙ СПОСОБ: кодируем строку в utf-8 перед проверкой
        assert "Поиск вакансий".encode("utf-8") in response.data
        assert "Нет найденных вакансий".encode("utf-8") in response.data


def test_vacancies_route_with_query(
    client: FlaskClient,
) -> None:
    """Test that filter parameters are correctly passed and displayed."""
    # Arrange
    with (
        patch("app.routes.get_filtered_vacancies", return_value=[]),
        patch("app.routes.get_total_vacancies_count", return_value=0),
        patch("app.routes.get_unique_sources", return_value=[]),
    ):
        # Act
        response = client.get("/vacancies?query=Python&location=Москва")

        # Assert
        assert response.status_code == 200
        assert b'value="Python"' in response.data
        assert 'value="Москва"'.encode("utf-8") in response.data


def test_trigger_parse_route(
    client: FlaskClient,
) -> None:
    """Test the '/trigger-parse' route.

    Ensures that a POST request correctly triggers the scheduler job.
    """
    # Arrange: Мокируем метод add_job у планировщика
    with patch("app.routes.scheduler.add_job") as mock_add_job:
        # Act: Выполняем POST-запрос
        response = client.post("/trigger-parse", data={"query": "Data Science"})

        # Assert
        # 1. Проверяем, что произошел редирект на страницу вакансий
        assert response.status_code == 302
        assert response.location == "/vacancies"

        # 2. Проверяем, что метод add_job был вызван один раз
        mock_add_job.assert_called_once()
        # 3. Проверяем, что он был вызван с правильным поисковым запросом
        _, call_kwargs = mock_add_job.call_args
        assert call_kwargs["args"][0] == "Data Science"
