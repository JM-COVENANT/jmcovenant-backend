"""
WSGI entrypoint for Gunicorn / Render:
    gunicorn wsgi:app --bind 0.0.0.0:$PORT
Exports: app = create_app()  (no module-level Flask() here)
"""
import os

# Render sets RENDER; default to production if APP_ENV not already set (e.g. in dashboard).
if (os.environ.get("RENDER") or "").lower() in ("1", "true", "yes"):
    os.environ.setdefault("APP_ENV", "production")

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app()
