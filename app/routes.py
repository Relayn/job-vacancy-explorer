"""Этот модуль определяет основные маршруты для Flask-приложения."""

import logging
from datetime import datetime
from math import ceil
from typing import Any

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import text

from core.database import (
    get_average_salary_by_city,
    get_db,
    get_filtered_vacancies,
    get_top_companies_by_vacancies,
    get_total_vacancies_count,
    get_unique_cities,
    get_unique_sources,
)
from core.extensions import scheduler
from core.scheduler import update_vacancies

bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@bp.route("/")
def index() -> Any:
    """Отображает главную страницу со статистикой.

    Returns:
        Ответ с отрендеренным шаблоном главной страницы.
    """
    with get_db() as db:
        stats: dict[str, Any] = {
            "total_vacancies": get_total_vacancies_count(db),
            "sources_count": len(get_unique_sources(db)),
            "cities_count": len(get_unique_cities(db)),
        }
    return render_template("index.html", stats=stats)


@bp.route("/vacancies")
def vacancies() -> Any:
    """Отображает страницу с вакансиями, фильтрами и пагинацией.

    Поддерживает фильтрацию по запросу, местоположению, компании, зарплате и источнику.

    Returns:
        Ответ с отрендеренным шаблоном страницы вакансий.
    """
    error_message = None
    try:
        query = request.args.get("query", type=str)
        location = request.args.get("location", type=str)
        company = request.args.get("company", type=str)
        salary_min = request.args.get("salary_min", type=int)
        salary_max = request.args.get("salary_max", type=int)
        source = request.args.get("source", type=str)
        sort = request.args.get("sort", "date", type=str)
        direction = request.args.get("direction", "desc", type=str)
        if direction not in ["asc", "desc"]:
            direction = "desc"  # Валидация
        sort_by = "salary" if sort == "salary" else "published_at"
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        page = max(1, page or 1)
        per_page = max(10, min(100, per_page or 20))

        with get_db() as db:
            current_vacancies = get_filtered_vacancies(
                db,
                page=page,
                per_page=per_page,
                query=query,
                location=location,
                company=company,
                salary_min=salary_min,
                salary_max=salary_max,
                source=source,
                sort_by=sort_by,
                sort_order=direction,
            )
            total_vacancies = get_total_vacancies_count(
                db,
                query=query,
                location=location,
                company=company,
                salary_min=salary_min,
                salary_max=salary_max,
                source=source,
            )
            sources = get_unique_sources(db)

        total_pages = ceil(total_vacancies / per_page) if total_vacancies > 0 else 1

    except Exception as e:
        logger.error("Ошибка при обработке запроса /vacancies: %s", e, exc_info=True)
        error_message = f"Произошла внутренняя ошибка сервера: {e}"
        current_vacancies, total_vacancies, total_pages, sources = [], 0, 1, []

    return render_template(
        "vacancies.html",
        vacancies=current_vacancies,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        total_vacancies=total_vacancies,
        query=query,
        location=location,
        company=company,
        salary_min=salary_min,
        salary_max=salary_max,
        source=source,
        sort=sort,
        direction=direction,
        sources=sources,
        error=error_message,
    )


@bp.route("/trigger-parse", methods=["POST"])
def trigger_parse() -> Any:
    """Запускает фоновую задачу парсинга вакансий.

    Returns:
        Редирект на страницу со списком вакансий после запуска задачи.
    """
    query = request.form.get("query", "Python")
    if not query:
        query = "Python"  # Запрос по умолчанию

    # Запускаем задачу один раз, немедленно
    scheduler.add_job(
        update_vacancies,
        "date",  # Триггер 'date' без run_date означает "запустить немедленно"
        args=[query],
        id=f"manual_parse_{datetime.now().timestamp()}",  # Уникальный ID для задачи
    )

    flash(
        f"Задача парсинга по запросу '{query}' запущена в фоновом режиме. "
        "Результаты появятся через несколько минут.",
        "success",
    )
    return redirect(url_for("main.vacancies"))


@bp.route("/analytics")
def analytics() -> Any:
    """Отображает страницу с аналитикой по вакансиям.

    Returns:
        Ответ с отрендеренным шаблоном страницы аналитики.
    """
    with get_db() as db:
        top_companies = get_top_companies_by_vacancies(db)
        salary_by_city = get_average_salary_by_city(db)

    return render_template(
        "analytics.html",
        top_companies=top_companies,
        salary_by_city=salary_by_city,
    )


@bp.route("/health")
def health_check() -> Any:
    """Проверяет состояние приложения и его зависимостей (БД).

    Returns:
        JSON-ответ со статусом 'ok' и кодом 200 в случае успеха,
        или 'error' и кодом 503, если есть проблемы с подключением к БД.
    """
    try:
        with get_db() as db:
            # Выполняем самый простой и быстрый запрос для проверки подключения
            db.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error("Health check failed: database connection error: %s", e)
        return (
            jsonify({"status": "error", "reason": "database connection failed"}),
            503,
        )
