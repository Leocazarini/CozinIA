"""FastAPI application entry point."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.recipes import router as recipes_router
from app.core.config import get_settings
from app.core.rate_limit import limiter

# Localhost origins allowed when no production origin is configured (dev). In
# production ALLOWED_ORIGIN pins CORS to the app's real https origin; the
# frontend actually reaches the API same-origin through the proxy, so this is
# only a backstop, never a wildcard.
_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost",
    "https://localhost",
]


def _cors_origins(allowed_origin: str | None) -> list[str]:
    return [allowed_origin] if allowed_origin else _DEV_ORIGINS


def _trusted_hosts(allowed_origin: str | None) -> list[str]:
    """Host header allowlist. Restricted to the real host in production; open
    in dev, where requests arrive as localhost / the container name."""
    if not allowed_origin:
        return ["*"]
    host = allowed_origin.split("://", 1)[-1]
    return [host, "localhost", "127.0.0.1"]


async def _rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """Answer a tripped rate limit with a Portuguese, user-facing message."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Muitas requisições em pouco tempo. Aguarde um momento e tente de novo.",
        },
    )


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    # Docs are turned off: this API is reached only by its own frontend, and an
    # open /docs/openapi.json is free reconnaissance for an attacker.
    application = FastAPI(
        title="CozinIA API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    # Rejects requests whose Host header isn't one we serve, closing Host-header
    # poisoning and the open-redirect surface it feeds.
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=_trusted_hosts(settings.allowed_origin),
    )

    # The SPA is served from its own origin (a different port in dev). CORS is
    # pinned to that origin — never a wildcard — so a random site the user
    # visits cannot drive the API on their behalf.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(settings.allowed_origin),
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(recipes_router)
    register_error_handlers(application)
    return application


app = create_app()
