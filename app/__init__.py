import logging

from flask import Flask
from markupsafe import Markup

from .routes import bp


def create_app():
    """
    Фабрика для создания экземпляра приложения Flask.
    Здесь происходит инициализация, регистрация blueprint'ов и запуск фоновых служб.
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
    def nl2br_filter(value):
        """Фильтр для преобразования символов новой строки в HTML-теги <br>."""
        if value:
            result = value.replace("\n", "<br>\n")
            return Markup(result)
        return value

    # Добавление функций max и min в глобальный контекст Jinja2
    app.jinja_env.globals.update(max=max, min=min)

    app.register_blueprint(bp)

    # --- ЗАПУСК ПЛАНИРОВЩИКА ---
    # Импортируем здесь, чтобы избежать циклических зависимостей
    from core.scheduler import start_scheduler

    start_scheduler()
    # ---------------------------

    return app
