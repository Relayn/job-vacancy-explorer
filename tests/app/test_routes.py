"""Модульные тесты для роутов Flask-приложения."""

from unittest.mock import patch

from flask.testing import FlaskClient


def test_index_route(
    client: FlaskClient,
) -> None:
    """Тестирует маршрут index ('/').

    Проверяет, что главная страница корректно загружается и отображает статистику.
    """
    # Arrange: Мокируем функции, обращающиеся к БД
    with (
        patch("app.routes.get_total_vacancies_count", return_value=123),
        patch("app.routes.get_unique_sources", return_value=["hh.ru", "superjob.ru"]),
        patch("app.routes.get_unique_cities", return_value=["Москва", "Казань"]),
    ):
        # Действие: выполняем GET-запрос к главной странице
        response = client.get("/")

        # Проверка: страница должна успешно загрузиться
        assert response.status_code == 200
        # Проверяем, что на странице отображается статистика из наших моков
        assert b"123" in response.data
        assert b"2" in response.data  # 2 источника
        assert b"2" in response.data  # 2 города


def test_vacancies_route_success(
    client: FlaskClient,
) -> None:
    """Тестирует маршрут '/vacancies' на успешный ответ.

    Убеждается, что страница загружается и корректно отображает информацию о вакансиях.
    """
    # Arrange: Мокируем все функции, которые вызывает эндпоинт
    with (
        patch("app.routes.get_filtered_vacancies", return_value=[]),
        patch("app.routes.get_total_vacancies_count", return_value=0),
        patch("app.routes.get_unique_sources", return_value=[]),
    ):
        # Действие: выполняем GET-запрос к странице вакансий
        response = client.get("/vacancies")

        # Проверка: успешный статус и наличие ключевых элементов
        assert response.status_code == 200
        # ПРАВИЛЬНЫЙ СПОСОБ: кодируем строку в utf-8 перед проверкой
        assert "Поиск вакансий".encode("utf-8") in response.data
        assert "Нет найденных вакансий".encode("utf-8") in response.data


def test_vacancies_route_with_query(
    client: FlaskClient,
) -> None:
    """Тестирует, что параметры фильтра корректно передаются и отображаются."""
    # Arrange
    with (
        patch("app.routes.get_filtered_vacancies", return_value=[]),
        patch("app.routes.get_total_vacancies_count", return_value=0),
        patch("app.routes.get_unique_sources", return_value=[]),
    ):
        # Действие
        response = client.get("/vacancies?query=Python&location=Москва")

        # Проверка
        assert response.status_code == 200
        assert b'value="Python"' in response.data
        assert 'value="Москва"'.encode("utf-8") in response.data


def test_trigger_parse_route(
    client: FlaskClient,
) -> None:
    """Тестирует маршрут '/trigger-parse'.

    Убеждается, что POST-запрос корректно запускает задачу в планировщике.
    """
    # Arrange: Мокируем метод add_job у планировщика
    with patch("app.routes.scheduler.add_job") as mock_add_job:
        # Действие: выполняем POST-запрос
        response = client.post("/trigger-parse", data={"query": "Data Science"})

        # Проверка
        # 1) Произошел редирект на страницу вакансий
        assert response.status_code == 302
        assert response.location == "/vacancies"

        # 2) Метод add_job был вызван один раз
        mock_add_job.assert_called_once()
        # 3) Он был вызван с правильным поисковым запросом
        _, call_kwargs = mock_add_job.call_args
        assert call_kwargs["args"][0] == "Data Science"


def test_health_check_route_ok(client: FlaskClient) -> None:
    """Тестирует эндпоинт /health на успешный ответ."""
    # Arrange: Мокируем get_db, чтобы он не вызывал реальную БД, а просто работал
    with patch("app.routes.get_db"):
        # Act
        response = client.get("/health")
        # Assert
        assert response.status_code == 200
        assert response.json == {"status": "ok"}


def test_analytics_route(client: FlaskClient) -> None:
    """Тестирует эндпоинт /analytics."""
    # Arrange: Мокируем функции, которые обращаются к БД
    with (
        patch("app.routes.get_top_companies_by_vacancies", return_value=[]),
        patch("app.routes.get_average_salary_by_city", return_value=[]),
    ):
        # Act
        response = client.get("/analytics")
        # Assert
        assert response.status_code == 200
        assert "Аналитика по вакансиям".encode("utf-8") in response.data
