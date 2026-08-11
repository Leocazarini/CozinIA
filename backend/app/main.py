"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.routes.health import router as health_router
from app.api.routes.recipes import router as recipes_router


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(title="Cozinia API")
    application.include_router(health_router)
    application.include_router(recipes_router)
    register_error_handlers(application)
    return application


app = create_app()
