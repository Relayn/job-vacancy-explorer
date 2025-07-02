# tests/conftest.py
import os
import sys

# Добавляем корневую директорию проекта в sys.path
# Это нужно, чтобы pytest мог находить модули приложения (core, app, parsers)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

print(f"[conftest.py] Added {project_root} to sys.path")
