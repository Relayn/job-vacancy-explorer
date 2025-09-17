"""Модуль для хранения экземпляров расширений Flask.

Помогает избежать циклических импортов.
"""

from apscheduler.schedulers.background import BackgroundScheduler

# Глобальный экземпляр планировщика для всего приложения
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
