import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

print(f"[conftest.py] Added {project_root} to sys.path")
print(f"[conftest.py] Current sys.path: ")
for p in sys.path:
    print(f"    {p}")
