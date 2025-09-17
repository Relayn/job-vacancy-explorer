"""Module for storing Flask extension instances.

This helps to avoid circular imports.
"""

from apscheduler.schedulers.background import BackgroundScheduler

# Создаем единственный экземпляр планировщика для всего приложения
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
