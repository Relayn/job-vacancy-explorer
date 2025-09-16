import logging
from datetime import datetime
from math import ceil

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core.database import (
    get_db,
    get_filtered_vacancies,
    get_total_vacancies_count,
    get_unique_cities,
    get_unique_sources,
)
from core.extensions import scheduler
from core.scheduler import update_vacancies

bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@bp.route("/")
def index():
    """Отображает главную страницу со статистикой."""
    with get_db() as db:
        stats = {
            "total_vacancies": get_total_vacancies_count(db),
            "sources_count": len(get_unique_sources(db)),
            "cities_count": len(get_unique_cities(db)),
        }
    return render_template("index.html", stats=stats)


@bp.route("/vacancies")
def vacancies():
    """Отображает страницу с вакансиями, фильтрами и пагинацией."""
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
        page = max(1, page)
        per_page = max(10, min(100, per_page))

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
def trigger_parse():
    """Запускает задачу парсинга в фоновом режиме."""
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
