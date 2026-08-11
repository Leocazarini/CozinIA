"""Specifications for the GET /health endpoint.

Given the backend can reach the database, the health endpoint reports the
system as operational; given it cannot, it reports the system as
unavailable so orchestration tooling (Docker healthchecks) can react.
"""

from fastapi.testclient import TestClient

from app.api.routes.health import get_is_database_reachable
from app.main import app


def test_given_database_reachable_when_getting_health_then_returns_ok_status() -> None:
    """Given the database is reachable, when GET /health is called,
    then it responds 200 with status "ok"."""
    app.dependency_overrides[get_is_database_reachable] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_given_database_unreachable_when_getting_health_then_returns_service_unavailable() -> None:
    """Given the database cannot be reached, when GET /health is called,
    then it responds 503 with status "error"."""
    app.dependency_overrides[get_is_database_reachable] = lambda: False
    try:
        client = TestClient(app)
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "error"}
