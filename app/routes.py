from flask import render_template, Blueprint, request
from core.database import (
    get_filtered_vacancies,
    get_total_vacancies_count,
    get_unique_sources,
    get_unique_cities,
)

bp = Blueprint("main", __name__)


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
        if vacancy["salary"] and (salary_min or salary_max):
            try:
                # Парсим зарплату из строки
                salary_text = vacancy["salary"].lower()
                # Удаляем нечисловые символы и разделяем на части
                import re

                salary_numbers = [int(s) for s in re.findall(r"\b\d+\b", salary_text)]

                if salary_numbers:
                    # Если указана минимальная зарплата и она больше максимальной в вакансии
                    if salary_min and int(salary_min) > max(salary_numbers):
                        matches_salary = False

                    # Если указана максимальная зарплата и она меньше минимальной в вакансии
                    if salary_max and int(salary_max) < min(salary_numbers):
                        matches_salary = False
                elif salary_min or salary_max:
                    # Если в зарплате нет чисел, но указан фильтр по зарплате, считаем несоответствие
                    matches_salary = False
            except (ValueError, TypeError):
                # В случае ошибки при парсинге зарплаты и наличия фильтра, считаем несоответствие
                if salary_min or salary_max:
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
