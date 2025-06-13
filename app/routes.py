from flask import render_template, Blueprint, request
from core.database import (
    get_filtered_vacancies,
    get_total_vacancies_count,
    get_unique_sources,
    get_unique_cities,
)
import re

bp = Blueprint("main", __name__)


def _parse_salary(salary_str: str) -> tuple[int | None, int | None]:
    """
    Parses a salary string and returns a tuple of (min_salary, max_salary).
    Handles formats like:
    - "от 100000 RUR" -> (100000, float('inf'))
    - "до 150000 RUR" -> (0, 150000)
    - "100000-150000 RUR" -> (100000, 150000)
    - "120000 RUR" -> (120000, 120000)
    - "без указания" or empty string -> (None, None)
    """
    if not salary_str or "без указания" in salary_str.lower():
        return None, None

    # Normalize the string: remove spaces, convert to lowercase, remove currency/units
    # Keep 'от' and 'до' for logic, then remove after checking their presence
    normalized_salary = salary_str.lower().replace(" ", "")

    numbers = [int(s) for s in re.findall(r"\d+", normalized_salary)]

    min_salary = None
    max_salary = None

    if "от" in normalized_salary and "до" in normalized_salary:
        if len(numbers) >= 2:
            min_salary = min(numbers)
            max_salary = max(numbers)
    elif "от" in normalized_salary:
        if numbers:
            min_salary = numbers[0]
            max_salary = float("inf")  # Open-ended max
    elif "до" in normalized_salary:
        if numbers:
            max_salary = numbers[0]
            min_salary = 0  # Open-ended min
    elif len(numbers) == 1:
        min_salary = numbers[0]
        max_salary = numbers[0]
    elif len(numbers) >= 2:  # For ranges like "100000-150000" without 'от'/'до'
        min_salary = min(numbers)
        max_salary = max(numbers)

    return min_salary, max_salary


def filter_vacancies(
    vacancies: list,
    query: str,
    location: str = "",
    company: str = "",
    salary_min: str = "",
    salary_max: str = "",
) -> list:
    """Фильтрует вакансии по запросу и другим параметрам."""
    filtered = []
    for vacancy in vacancies:
        # Проверка на соответствие запросу (в названии, компании или местоположении)
        matches_query = not query or (
            query.lower() in vacancy["title"].lower()
            or query.lower() in vacancy["company"].lower()
            or query.lower() in vacancy["location"].lower()
        )

        # Проверка на соответствие местоположению
        matches_location = (
            not location or location.lower() in vacancy["location"].lower()
        )

        # Проверка на соответствие компании
        matches_company = not company or company.lower() in vacancy["company"].lower()

        # Проверка на соответствие зарплате (если она указана)
        matches_salary = True
        if salary_min or salary_max:
            parsed_min_salary, parsed_max_salary = _parse_salary(
                vacancy.get("salary", "")
            )

            if parsed_min_salary is None and parsed_max_salary is None:
                matches_salary = False  # No valid salary range could be parsed
            else:
                try:
                    # Convert filter values to integers, None if empty
                    filter_min = int(salary_min) if salary_min else None
                    filter_max = int(salary_max) if salary_max else None

                    # Use -inf and +inf for open-ended ranges for easier comparison
                    vac_min_comp = (
                        parsed_min_salary
                        if parsed_min_salary is not None
                        else -float("inf")
                    )
                    vac_max_comp = (
                        parsed_max_salary
                        if parsed_max_salary is not None
                        else float("inf")
                    )

                    fil_min_comp = (
                        filter_min if filter_min is not None else -float("inf")
                    )
                    fil_max_comp = (
                        filter_max if filter_max is not None else float("inf")
                    )

                    # Check for overlap: max(start1, start2) <= min(end1, end2)
                    # For interval [A, B] and [C, D], they overlap if max(A, C) <= min(B, D)
                    if not (
                        max(vac_min_comp, fil_min_comp)
                        <= min(vac_max_comp, fil_max_comp)
                    ):
                        matches_salary = False

                except (ValueError, TypeError):
                    matches_salary = False

        # Если вакансия соответствует всем критериям, добавляем её в отфильтрованный список
        if matches_query and matches_location and matches_company and matches_salary:
            filtered.append(vacancy)

    return filtered


@bp.route("/")
def index():
    # Получаем статистику для главной страницы
    stats = {
        "total_vacancies": get_total_vacancies_count(),
        "sources_count": len(get_unique_sources()),
        "cities_count": len(get_unique_cities()),
    }
    return render_template("index.html", stats=stats)


@bp.route("/vacancies")
def vacancies():
    try:
        # Получаем параметры фильтрации
        query = request.args.get("query", "")
        location = request.args.get("location", "")
        company = request.args.get("company", "")
        salary_min = request.args.get("salary_min", "")
        salary_max = request.args.get("salary_max", "")

        # Получаем параметр сортировки
        sort = request.args.get("sort", "date")

        # Определяем поле и направление сортировки
        if sort == "salary":
            order_by = "salary"  # Сортировка по зарплате
        else:
            order_by = "published_at"  # По умолчанию сортировка по дате

        order_direction = "DESC"  # По умолчанию сортируем по убыванию (новые сверху)

        # Получаем параметры пагинации
        try:
            page = max(1, int(request.args.get("page", 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            per_page = min(100, max(10, int(request.args.get("per_page", 50))))
        except (ValueError, TypeError):
            per_page = 50

        # Используем новые оптимизированные функции для работы с БД
        current_vacancies = get_filtered_vacancies(
            query=query,
            location=location,
            company=company,
            page=page,
            per_page=per_page,
            order_by=order_by,
            order_direction=order_direction,
        )

        # Общее количество вакансий для пагинации
        total_vacancies = get_total_vacancies_count(
            query=query, location=location, company=company
        )

        # Рассчитываем общее количество страниц
        total_pages = max(1, (total_vacancies + per_page - 1) // per_page)

        # Если у нас есть фильтры по зарплате, применяем их постобработкой
        # (так как зарплата хранится в текстовом формате и её сложно фильтровать в SQL)
        if salary_min or salary_max:
            current_vacancies = filter_vacancies(
                current_vacancies,
                query="",  # Основной поиск уже выполнен в SQL
                location="",  # Локация уже отфильтрована в SQL
                company="",  # Компания уже отфильтрована в SQL
                salary_min=salary_min,
                salary_max=salary_max,
            )

            # Если количество вакансий после фильтрации по зарплате сильно уменьшилось,
            # возможно, нам понадобится получить дополнительные вакансии
            if len(current_vacancies) < per_page // 2 and total_vacancies > per_page:
                # Получаем больше вакансий для компенсации отфильтрованных
                additional_vacancies = get_filtered_vacancies(
                    query=query,
                    location=location,
                    company=company,
                    page=page + 1,
                    per_page=per_page,
                    order_by=order_by,
                    order_direction=order_direction,
                )

                # Фильтруем дополнительные вакансии и добавляем их к текущим
                filtered_additional = filter_vacancies(
                    additional_vacancies,
                    query="",
                    location="",
                    company="",
                    salary_min=salary_min,
                    salary_max=salary_max,
                )

                current_vacancies.extend(filtered_additional)
                # Ограничиваем количество вакансий до per_page
                current_vacancies = current_vacancies[:per_page]

        # Передаем данные в шаблон
        return render_template(
            "vacancies.html",
            vacancies=current_vacancies,
            query=query,
            location=location,
            company=company,
            salary_min=salary_min,
            salary_max=salary_max,
            page=page,
            total_pages=total_pages,
            per_page=per_page,
            total_vacancies=total_vacancies,
            sort=sort,
        )

    except Exception as e:
        # Логируем ошибку
        import traceback

        print(f"Ошибка при обработке запроса: {str(e)}")
        print(traceback.format_exc())
        # Возвращаем страницу с сообщением об ошибке
        return (
            render_template(
                "vacancies.html",
                vacancies=[],
                query="",
                location="",
                company="",
                salary_min="",
                salary_max="",
                page=1,
                total_pages=1,
                per_page=20,
                total_vacancies=0,
                sort="date",
                error=f"Произошла ошибка при обработке запроса: {str(e)}",
            ),
            500,
        )
