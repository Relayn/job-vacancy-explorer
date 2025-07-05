# Job Vacancy Explorer (Агрегатор Вакансий)

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Pipeline](https://github.com/Relayn/job-vacancy-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/Relayn/job-vacancy-explorer/actions/workflows/ci.yml)

Job Vacancy Explorer — это веб-приложение для агрегации, поиска и фильтрации вакансий. Приложение автоматически собирает данные с HeadHunter и SuperJob, сохраняет их в базе данных PostgreSQL и предоставляет удобный веб-интерфейс для пользователей.

## 🚀 Ключевые возможности

*   **Агрегация из нескольких источников**: Собирает вакансии с `hh.ru` и `superjob.ru`.
*   **Автоматическое обновление**: Фоновый планировщик (`APScheduler`) регулярно обновляет базу данных.
*   **Ручной запуск парсинга**: Возможность запустить сбор вакансий по конкретному запросу прямо из интерфейса.
*   **Продвинутый поиск и фильтрация**:
    *   Полнотекстовый поиск PostgreSQL по названию и описанию.
    *   Фильтрация по местоположению, компании, источнику.
    *   Фильтрация по диапазону заработной платы.
*   **Удобный интерфейс**: Современный и адаптивный интерфейс на базе Bootstrap 5.
*   **Сортировка и пагинация**: Результаты можно сортировать по дате или зарплате, а также просматривать постранично.

## 🛠️ Технологический стек

*   **Бэкенд**: Python, Flask, Gunicorn
*   **База данных**: PostgreSQL
*   **Миграции**: Alembic
*   **ORM**: SQLAlchemy
*   **Парсинг**: Requests, BeautifulSoup4
*   **Планировщик задач**: APScheduler
*   **Контейнеризация**: Docker, Docker Compose
*   **CI/CD**: GitHub Actions
*   **Качество кода**: Ruff, Black, pre-commit

## ⚙️ Установка и запуск через Docker

Этот проект полностью контейнеризирован, что делает его запуск максимально простым.

### 1. Предварительные требования

*   **Docker**
*   **Docker Compose**

### 2. Клонирование репозитория

```bash
git clone https://github.com/Relayn/job-vacancy-explorer.git
cd job-vacancy-explorer
```

### 3. Настройка окружения

Создайте файл `.env` на основе примера `.env.example`.

*   **Для macOS/Linux:**
    ```bash
    cp .env.example .env
    ```
*   **Для Windows:**
    ```bash
    copy .env.example .env
    ```
Вы можете оставить значения по умолчанию или изменить их при необходимости.

### 4. Запуск проекта

Выполните одну команду:

```bash
docker-compose up --build -d
```

Эта команда сделает всё необходимое:
1.  Соберет Docker-образ для Flask-приложения.
2.  Запустит контейнеры для приложения (`app`) и базы данных (`db`).
3.  Создаст volume для сохранения данных PostgreSQL.

Приложение будет доступно по адресу [http://localhost:8001](http://localhost:8001).

### 5. Применение миграций базы данных

При первом запуске или после изменений в моделях данных необходимо применить миграции:

```bash
docker-compose exec app alembic upgrade head
```

### 6. Остановка проекта

```bash
docker-compose down
```

Для удаления данных PostgreSQL (например, для полного сброса) используйте:
```bash
docker-compose down -v
```

## 🧪 Тестирование

Проект покрыт двумя типами тестов: **unit** и **integration**.

### Unit-тесты

Эти тесты быстрые, изолированные и не требуют реальной базы данных (используют SQLite в памяти). Они проверяют логику отдельных функций и классов.

Для запуска только unit-тестов выполните:
```bash
docker-compose exec -e TEST_DATABASE_URL="sqlite:///:memory:" app poetry run pytest -m "not integration"
```

### Интеграционные тесты

Эти тесты проверяют взаимодействие компонентов системы, в первую очередь — корректность подключения и работы с реальной базой данных PostgreSQL.

Для запуска только интеграционных тестов выполните:
```bash
docker-compose exec app poetry run pytest -m "integration"
```

## ⚖️ Лицензия

Этот проект распространяется под лицензией MIT. Подробности смотрите в файле [LICENSE](LICENSE).
```
