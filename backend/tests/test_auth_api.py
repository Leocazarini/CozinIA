"""Specifications for authentication: logging in, and the gate it puts in
front of every recipe endpoint.

Exercises the real login flow (password hashing, token issuing, token
verification) against the Postgres test database — nothing here is stubbed, so
a broken hash or a mis-signed token would surface.
"""

from collections.abc import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import get_db_session
from app.core.rate_limit import limiter
from app.main import app
from app.models.user import User
from app.services.auth_service import hash_password

_USERNAME = "leo"
_PASSWORD = "uma-senha-bem-comprida-123"


async def _override_get_db_session() -> AsyncGenerator:
    engine = create_async_engine(get_settings().test_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _seed_user_and_clean() -> AsyncGenerator[None, None]:
    """Seed one account before each test and wipe the users table after."""
    engine = create_async_engine(get_settings().test_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add(User(username=_USERNAME, password_hash=hash_password(_PASSWORD)))
        await session.commit()
    await engine.dispose()

    yield

    engine = create_async_engine(get_settings().test_database_url)
    async with engine.begin() as connection:
        await connection.execute(delete(User))
    await engine.dispose()


@pytest.fixture
def client() -> Callable[[], TestClient]:
    app.dependency_overrides[get_db_session] = _override_get_db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _login(client: TestClient, username: str = _USERNAME, password: str = _PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_given_correct_credentials_when_logging_in_then_a_token_is_returned(
    client: TestClient,
) -> None:
    """Given a real account and its password, when POSTing to /api/auth/login,
    then a bearer token is returned."""
    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_given_a_wrong_password_when_logging_in_then_it_is_rejected(client: TestClient) -> None:
    """Given a real account but the wrong password, when logging in, then a 401
    with a message that does not reveal whether the user exists is returned."""
    response = _login(client, password="senha-errada")

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário ou senha inválidos."


def test_given_an_unknown_user_when_logging_in_then_the_same_rejection_is_returned(
    client: TestClient,
) -> None:
    """Given a username that doesn't exist, when logging in, then the rejection
    is byte-identical to the wrong-password one — no user enumeration."""
    response = _login(client, username="ninguem")

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário ou senha inválidos."


def test_given_a_valid_token_when_calling_a_protected_route_then_it_is_allowed(
    client: TestClient,
) -> None:
    """Given a token from a successful login, when calling a protected recipe
    route with it, then the request is allowed through the auth gate."""
    token = _login(client).json()["access_token"]

    response = client.get("/api/recipes", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_given_no_token_when_calling_a_protected_route_then_it_is_rejected(
    client: TestClient,
) -> None:
    """Given no Authorization header, when calling a protected recipe route,
    then a 401 is returned and nothing behind the gate runs."""
    response = client.get("/api/recipes")

    assert response.status_code == 401


def test_given_a_garbage_token_when_calling_a_protected_route_then_it_is_rejected(
    client: TestClient,
) -> None:
    """Given a token that isn't a valid signed JWT, when calling a protected
    route, then it is refused."""
    response = client.get("/api/recipes", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


def test_given_a_valid_token_when_asking_who_am_i_then_the_username_is_returned(
    client: TestClient,
) -> None:
    """Given a valid token, when GETting /api/auth/me, then the signed-in
    username is returned — how the frontend confirms a stored token still
    works."""
    token = _login(client).json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == _USERNAME


def test_given_repeated_failed_logins_when_the_limit_is_passed_then_they_are_throttled(
    client: TestClient,
) -> None:
    """Given many login attempts from one caller, when the per-minute limit is
    exceeded, then further attempts are answered with 429 — blunting a
    brute-force. Rate limiting is turned on only for this test (the suite runs
    with it off, see conftest.py)."""
    limiter.enabled = True
    try:
        statuses = [_login(client, password="errada").status_code for _ in range(15)]
    finally:
        limiter.enabled = False

    assert 429 in statuses
