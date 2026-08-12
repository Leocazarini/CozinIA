"""Specifications for CORS support.

The frontend SPA is served from its own origin (a different port in dev,
potentially a different domain in production) — the browser enforces CORS
on every call it makes to the API, so without explicit headers the app
would be unable to load or save anything, even though server-to-server
requests (e.g. curl, the test client itself without Origin headers) work
fine and would never surface the problem.

Exercised against /health (rather than a data route) so these tests don't
need a real database — CORS is global middleware, unrelated to the route.
"""

from fastapi.testclient import TestClient

from app.api.routes.health import get_is_database_reachable
from app.main import app


def test_given_a_preflight_request_from_the_frontend_when_checked_then_cors_headers_allow_it() -> (
    None
):
    """Given a browser preflighting a GET to the API from another origin,
    when the API responds, then it allows the request via CORS headers."""
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_given_a_get_request_from_the_frontend_when_it_completes_then_cors_headers_allow_reading_it() -> (
    None
):
    """Given a browser's actual (non-preflighted) GET request, when the API
    responds, then the response still carries the CORS header the browser
    needs to expose the body to the page's JavaScript."""
    app.dependency_overrides[get_is_database_reachable] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    finally:
        app.dependency_overrides.clear()

    assert response.headers["access-control-allow-origin"] == "*"
