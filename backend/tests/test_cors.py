"""Specifications for CORS support.

The frontend SPA is served from its own origin (a different port in dev,
potentially a different domain in production) — the browser enforces CORS
on every call it makes to the API, so without explicit headers the app
would be unable to load or save anything, even though server-to-server
requests (e.g. curl, the test client itself without Origin headers) work
fine and would never surface the problem.

CORS is pinned to the frontend's own origin — never a wildcard — so a random
site the user visits cannot drive the API on their behalf. With no
ALLOWED_ORIGIN configured (the case under test), a small set of localhost dev
origins is allowed and every other origin is refused.

Exercised against /health (rather than a data route) so these tests don't
need a real database — CORS is global middleware, unrelated to the route.
"""

from fastapi.testclient import TestClient

from app.api.routes.health import get_is_database_reachable
from app.main import app

_FRONTEND_ORIGIN = "http://localhost:5173"


def test_given_a_preflight_request_from_the_frontend_when_checked_then_cors_headers_allow_it() -> (
    None
):
    """Given a browser preflighting a GET to the API from the frontend origin,
    when the API responds, then it allows the request by echoing that exact
    origin (not a wildcard)."""
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": _FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _FRONTEND_ORIGIN


def test_given_a_get_request_from_the_frontend_when_it_completes_then_cors_headers_allow_reading_it() -> (
    None
):
    """Given a browser's actual (non-preflighted) GET request from the frontend
    origin, when the API responds, then the response carries the CORS header
    the browser needs to expose the body to the page's JavaScript."""
    app.dependency_overrides[get_is_database_reachable] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/health", headers={"Origin": _FRONTEND_ORIGIN})
    finally:
        app.dependency_overrides.clear()

    assert response.headers["access-control-allow-origin"] == _FRONTEND_ORIGIN


def test_given_a_request_from_an_unknown_origin_when_preflighted_then_it_is_not_allowed() -> None:
    """Given a preflight from an origin that isn't the frontend, when the API
    responds, then it does not hand back an allow-origin header for it — the
    wildcard that used to green-light any site is gone."""
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"
    assert response.headers.get("access-control-allow-origin") != "*"
