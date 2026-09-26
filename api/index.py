# Vercel entry point — imports the FastAPI app from app/main.py
import sys
import os

# Ensure the project root is on the path so `app.*` imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: F401 — Vercel picks up `app`
