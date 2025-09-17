"""Main application package."""

import logging

from flask import Flask
from markupsafe import Markup, escape

from .routes import bp


def create_app() -> Flask:
    """Create and configure an instance of the Flask application.

    This function acts as a factory for the Flask application. It handles
    initialization, blueprint registration, and the startup of background
    services.
    """
    # --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # -----------------------------

    app = Flask(__name__)

    # Регистрация пользовательского фильтра nl2br
    @app.template_filter("nl2br")
    def nl2br_filter(value: str | None) -> Markup:
        """Convert newlines in a string to HTML <br> tags, ensuring safety."""
        if not value:
            return Markup("")
        # Сначала экранируем ВСЕ данные, потом безопасно заменяем \n на <br>
        escaped_value = escape(value)
        result = escaped_value.replace("\n", Markup("<br>\n"))
        return result

    # Добавление функций max и min в глобальный контекст Jinja2
    app.jinja_env.globals.update(max=max, min=min)

    app.register_blueprint(bp)

    # --- ЗАПУСК ПЛАНИРОВЩИКА ---
    # Импортируем здесь, чтобы избежать циклических зависимостей
    from core.scheduler import start_scheduler

    start_scheduler()
    # ---------------------------

    return app
