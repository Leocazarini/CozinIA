"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(title="Cozinia API")
    application.include_router(health_router)
    return application


app = create_app()
