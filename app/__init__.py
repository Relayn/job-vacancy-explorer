# Flask app initialization
from flask import Flask
from .routes import bp
from markupsafe import Markup


def create_app():
    """
    Фабрика для создания экземпляра приложения Flask.
    Здесь происходит инициализация, регистрация blueprint'ов и запуск фоновых служб.
    """
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
