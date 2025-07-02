# app/routes.py
from math import ceil

from flask import Blueprint, render_template, request

from core.database import (
    get_db,
    get_filtered_vacancies,
    get_total_vacancies_count,
    get_unique_cities,
    get_unique_sources,
)

bp = Blueprint("main", __name__)


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
        # --- Параметры фильтрации ---
        query = request.args.get("query", type=str)
        location = request.args.get("location", type=str)
        company = request.args.get("company", type=str)
        salary_min = request.args.get("salary_min", type=int)
        salary_max = request.args.get("salary_max", type=int)
        source = request.args.get("source", type=str)

        # --- Параметры сортировки ---
        sort = request.args.get("sort", "date", type=str)
        sort_by = "salary_max_rub" if sort == "salary" else "published_at"

        # --- Параметры пагинации ---
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        page = max(1, page)
        per_page = max(10, min(100, per_page))

        with get_db() as db:
            # Получаем вакансии и общее количество с учетом всех фильтров
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
            # Получаем списки для фильтров
            sources = get_unique_sources(db)

        total_pages = ceil(total_vacancies / per_page) if total_vacancies > 0 else 1

    except Exception as e:
        import traceback

        print(f"Ошибка при обработке запроса: {e}")
        print(traceback.format_exc())
        error_message = f"Произошла внутренняя ошибка сервера: {e}"
        # В случае ошибки возвращаем пустые данные
        current_vacancies = []
        total_vacancies = 0
        total_pages = 1
        sources = []

    return render_template(
        "vacancies.html",
        vacancies=current_vacancies,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        total_vacancies=total_vacancies,
        # Возвращаем параметры для сохранения в форме
        query=query,
        location=location,
        company=company,
        salary_min=salary_min,
        salary_max=salary_max,
        source=source,
        sort=sort,
        sources=sources,
        error=error_message,
    )
