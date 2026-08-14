"""Shared rate limiter.

Caps how often a single caller can hit the expensive, money-spending endpoints
(recipe creation, which calls paid AI models) and the login endpoint (to blunt
password guessing). Registered on the app in app/main.py; individual limits are
declared with @limiter.limit(...) at each route.
"""

from slowapi import Limiter
from starlette.requests import Request


def _client_identifier(request: Request) -> str:
    """Identify the caller for rate limiting, honoring the proxy chain.

    The backend sits behind nginx (and, in production, Cloudflare), so
    request.client.host is the proxy, not the user. Prefer the address the
    edge reports. These headers are only trustworthy because the backend is
    not reachable directly — nginx sets them and the port is never published.
    """
    cloudflare_ip = request.headers.get("CF-Connecting-IP")
    if cloudflare_ip:
        return cloudflare_ip
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "anonymous"


limiter = Limiter(key_func=_client_identifier)

# The three doors that spend OpenRouter credits and do heavy work (download,
# transcode, multiple model calls). Kept as a name so the routes and any future
# tuning stay in one place.
CREATE_RECIPE_LIMIT = "10/minute"

# Login is cheap but a brute-force target; keep it tight per source address.
LOGIN_LIMIT = "10/minute"
