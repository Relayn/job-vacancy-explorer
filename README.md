#  Job Vacancy Explorer (Агрегатор Вакансий)

<p align="left">
  <!-- Статус и Качество -->
  <a href="https://github.com/Relayn/job-vacancy-explorer/actions/workflows/ci.yml">
    <img src="https://github.com/Relayn/job-vacancy-explorer/actions/workflows/ci.yml/badge.svg" alt="CI Pipeline">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Coverage-90%25-brightgreen" alt="Test Coverage">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Ruff-checked-blue" alt="Checked with Ruff">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Mypy-strict-blue" alt="Strictly typed with Mypy">
  </a>
  <!-- Технологии -->
  <br/>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11">
  </a>
  <a href="https://flask.palletsprojects.com/">
    <img src="https://img.shields.io/badge/Flask-3.0-black?logo=flask&logoColor=white" alt="Flask">
  </a>
  <a href="https://www.postgresql.org/">
    <img src="https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql&logoColor=white" alt="PostgreSQL">
  </a>
  <a href="https://www.docker.com/">
    <img src="https://img.shields.io/badge/Docker-enabled-blue?logo=docker&logoColor=white" alt="Docker Enabled">
  </a>
  <!-- Лицензия -->
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License: MIT">
  </a>
</p>

**Job Vacancy Explorer** — это полностью автоматизированный агрегатор вакансий, который собирает, анализирует и представляет данные с ведущих российских платформ по поиску работы. Проект разработан с акцентом на надежность, качество кода и безопасность, используя современные практики DevOps и CI/CD.

---

![Project Screenshot](docs/screenshot.png)

## 🌟 Ключевые возможности

*   **Автоматическая агрегация:** Фоновый планировщик (`APScheduler`) регулярно собирает свежие вакансии с `hh.ru` и `superjob.ru`.
*   **Продвинутый поиск:** Мощный полнотекстовый поиск PostgreSQL по названию и описанию.
*   **Гибкая фильтрация:** Фильтрация результатов по местоположению, компании, источнику и диапазону заработной платы.
*   **Нормализация данных:** Вся информация о зарплате, независимо от валюты и формата ("от", "до", вилка), автоматически конвертируется в рубли для удобной сортировки и фильтрации.
*   **Ручной запуск:** Возможность запустить парсинг по кастомному запросу прямо из веб-интерфейса.
*   **Современный интерфейс:** Чистый, адаптивный и интуитивно понятный UI на базе Bootstrap 5.

## 🛠️ Технологический стек и архитектура

Проект построен на надежном и масштабируемом стеке с четким разделением ответственности между компонентами.

| Категория          | Технологии                                                              |
| ------------------ | ----------------------------------------------------------------------- |
| **Бэкенд**         | `Python 3.11`, `Flask`, `Gunicorn`, `SQLAlchemy (ORM)`                  |
| **База данных**    | `PostgreSQL 16`, `Alembic` (для миграций схемы)                         |
| **Парсинг**        | `Requests`, `BeautifulSoup4`, `Pydantic` (для валидации и DTO)          |
| **DevOps**         | `Docker`, `Docker Compose`, `GitHub Actions` (CI/CD)                    |
| **Качество кода**  | `Pytest`, `pytest-cov` (90% покрытие), `Ruff`, `Mypy`, `Bandit`, `pre-commit` |

### Диаграмма архитектуры

```mermaid
graph TD
    subgraph "Внешний мир"
        A[Пользователь]
        HHRU[hh.ru API]
        SJ[superjob.ru HTML]
    end

    subgraph "Приложение (Docker)"
        B(Flask / Gunicorn)
        C(PostgreSQL)
        D(Планировщик APScheduler)
        F(Парсеры)
    end

    A -- HTTP-запросы --> B
    B -- SQLAlchemy ORM --> C
    D -- Запускает по расписанию --> F
    F -- HTTP-запросы --> HHRU
    F -- HTTP-запросы --> SJ
    F -- DTO (Pydantic) --> B
```

## 🚀 Как запустить проект

Проект полностью контейнеризирован с помощью Docker, что обеспечивает быстрый и предсказуемый запуск на любой системе.

### 1. Предварительные требования

*   **Docker**
*   **Docker Compose**

### 2. Установка

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/Relayn/job-vacancy-explorer.git
    cd job-vacancy-explorer
    ```

2.  **Создайте файл окружения:**
    Скопируйте файл `.env.example` в `.env`. Значения по умолчанию подходят для локального запуска.
    ```bash
    # Для Windows
    copy .env.example .env
    # Для macOS/Linux
    cp .env.example .env
    ```

3.  **Запустите Docker Compose:**
    Эта команда соберет образ, создаст тома и запустит контейнеры приложения и базы данных.
    ```bash
    docker-compose up --build -d
    ```

4.  **Примените миграции базы данных:**
    При первом запуске необходимо создать таблицы в базе данных.
    ```bash
    docker-compose exec app alembic upgrade head
    ```

✅ **Готово!** Приложение будет доступно по адресу, указанному в вашем `docker-compose.yml` (например, [http://localhost:8076](http://localhost:8076)).

## ✅ Качество и надежность

Этот проект был разработан с использованием практик, обеспечивающих высокое качество кода, безопасность и стабильность.

*   **CI/CD Пайплайн:** Каждый коммит автоматически проходит через 4-этапный пайплайн в **GitHub Actions**, который включает:
    1.  **Линтинг и статический анализ** (`Ruff`, `Mypy`).
    2.  **Unit-тесты** (с проверкой покрытия >90%).
    3.  **Сканирование безопасности** (`Bandit`, `pip-audit`).
    4.  **Интеграционные тесты** с реальной базой данных PostgreSQL.

*   **Высокое покрытие тестами:** Проект имеет **90% покрытие кода** unit-тестами, что гарантирует надежность бизнес-логики.

*   **Автоматическое обновление зависимостей:** `Dependabot` настроен для автоматического создания Pull Request'ов при появлении обновлений безопасности для зависимостей.

*   **Безопасность по умолчанию:** Используется `Pydantic Settings` для управления конфигурацией через переменные окружения, что исключает попадание секретов в код. ORM защищает от SQL-инъекций.

## 🗺️ Дальнейшее развитие (Roadmap)

- [ ] **Создание страницы "Аналитика"** с визуализацией данных (средние зарплаты, топ компаний).
- [ ] **Оптимизация Docker-образа** для production с использованием multi-stage builds.
- [ ] **Добавление эндпоинта `/health`** для мониторинга состояния приложения.

## ⚖️ Лицензия

Проект распространяется под лицензией MIT. Подробности смотрите в файле [LICENSE](LICENSE).
