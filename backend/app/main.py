"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes.health import router as health_router
from app.api.routes.recipes import router as recipes_router


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(title="CozinIA API")
    # The SPA is served from its own origin (a different port in dev,
    # potentially a different domain later) — without this, the browser
    # blocks every request the frontend makes. Single-user app with no
    # cookie-based auth, so a wildcard origin carries no extra risk.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(recipes_router)
    register_error_handlers(application)
    return application


app = create_app()
