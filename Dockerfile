# Этап 1: Базовый образ с Python
FROM python:3.11-slim AS base

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем системные зависимости, необходимые для сборки некоторых пакетов
RUN apt-get update && apt-get install -y build-essential

# Устанавливаем Poetry
RUN pip install poetry

# Конфигурируем Poetry, чтобы он не создавал venv внутри проекта
RUN poetry config virtualenvs.create false


# Этап 2: Установка зависимостей
FROM base AS builder

# Копируем файлы для установки зависимостей
COPY pyproject.toml poetry.lock* ./

# Устанавливаем все зависимости, включая dev, для тестирования и линтинга
# --no-interaction и --no-ansi для чистого вывода в логах
RUN poetry install --no-interaction --no-ansi

# Этап 3: Финальный образ
FROM base

# Копируем установленные зависимости из builder
# 1. Копируем библиотеки
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# 2. Копируем исполняемые файлы (gunicorn, alembic, etc.)
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Копируем исходный код приложения
COPY . .

# Открываем порт, на котором будет работать Gunicorn
EXPOSE 8000

# Команда для запуска приложения через Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--preload", "run:app"]
