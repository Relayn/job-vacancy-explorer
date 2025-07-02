# alembic/env.py
import os
import sys
from logging.config import fileConfig

# --- НАЧАЛО ИСПРАВЛЕНИЯ ---
# Добавляем путь к проекту в самое начало, ДО всех импортов.
# Это позволяет Python найти наши модули (core, etc.)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from core.config import settings
from core.models import Base

# Загружаем переменные окружения. Теперь это можно сделать здесь,
# так как все импорты стандартных библиотек уже прошли.
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Устанавливаем URL для подключения к БД из нашего файла конфигурации
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
