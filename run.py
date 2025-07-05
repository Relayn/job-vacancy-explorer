import os

from app import create_app

app = create_app()

# Устанавливаем секретный ключ. В реальном проекте его лучше брать из переменных окружения.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24))

if __name__ == "__main__":
    # Этот блок нужен для локального запуска (python run.py).
    # Gunicorn использует этот файл, но не этот блок.
    # Планировщик уже запущен внутри create_app().
    app.run(debug=True, host="0.0.0.0", port=5000)
