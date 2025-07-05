"""
Модуль для хранения экземпляров расширений Flask (и подобных объектов),
чтобы избежать циклических импортов.
"""

from apscheduler.schedulers.background import BackgroundScheduler

# Создаем единственный экземпляр планировщика для всего приложения
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
