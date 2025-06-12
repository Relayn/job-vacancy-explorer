import sqlite3
from tabulate import tabulate


def view_vacancies(limit=10):
    conn = sqlite3.connect("vacancies.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vacancies LIMIT ?", (limit,))
    vacancies = cursor.fetchall()

    if not vacancies:
        print("Нет сохраненных вакансий")
        return

    headers = ["ID", "Название", "Компания", "Локация", "Зарплата", "Описание", "Дата", "Источник"]
    print(tabulate(vacancies, headers=headers, tablefmt="grid"))

    conn.close()


if __name__ == "__main__":
    view_vacancies(limit=20)  # Показать 20 вакансий