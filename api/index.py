# Vercel entry point – re‑export FastAPI app for the serverless platform
# Vercel expects a callable named ``handler`` for Python runtimes.
# We simply import the FastAPI app instance defined in ``backend/app/main.py``.

from backend.app.main import app as handler

# The name ``handler`` is required by Vercel's Python serverless bridge.
