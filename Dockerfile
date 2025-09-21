# Этап 1: Builder - сборка зависимостей
FROM python:3.11-slim AS builder

# Устанавливаем переменные окружения для Poetry
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"

# Устанавливаем системные зависимости, необходимые для сборки, и сам Poetry
# Используем curl для установки Poetry, как рекомендовано официально
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://install.python-poetry.org | python3 -

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей и устанавливаем ТОЛЬКО production-зависимости
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# Этап 2: Production - финальный, легковесный образ
FROM python:3.11-slim AS production-image

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Создаем пользователя с ограниченными правами для запуска приложения
# Это ключевая практика безопасности
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Копируем установленные зависимости из builder'а
# Сначала библиотеки...
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# ...а теперь исполняемые файлы (gunicorn, alembic и т.д.)
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем исходный код приложения
# .dockerignore гарантирует, что лишние файлы не попадут в образ
COPY . .

# Меняем владельца файлов на нашего пользователя
RUN chown -R appuser:appgroup /app

# Переключаемся на пользователя с ограниченными правами
USER appuser

# Открываем порт, на котором будет работать Gunicorn
EXPOSE 8000

# Команда для запуска приложения: сначала миграции, потом сервер
CMD ["sh", "-c", "alembic upgrade head && gunicorn --bind 0.0.0.0:8000 run:app"]
