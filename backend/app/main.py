# FastAPI application factory – sets up CORS and includes routes
# Used by both local development and Vercel deployment.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

def create_app() -> FastAPI:
    """Create and configure the FastAPI app instance."""
    app = FastAPI(title="Log Analyzer API", version="0.1.0")
    # Allow any origin for demo; adjust in production as needed.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app

# Export a global app for ASGI servers.
app = create_app()
