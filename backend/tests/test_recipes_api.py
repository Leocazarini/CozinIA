"""Specifications for the recipe API endpoints (create/list/get/update/delete).

Exercises the full HTTP stack via TestClient against the real Postgres test
database. Scraping and AI extraction are stubbed — no real network or model
calls are made — including the paths that map domain exceptions to
user-facing (Portuguese) HTTP responses.
"""

import uuid
from collections.abc import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.recipes import get_recipe_service
from app.core.config import get_settings
from app.core.db import get_db_session
from app.main import app
from app.models.recipe import Recipe
from app.schemas.recipe import IngredientExtraction, RecipeExtraction, StepExtraction
from app.services.ai_extractor import AIRequestError
from app.services.recipe_service import RecipeService
from app.services.scraper import UnreachableUrlError

FAKE_EXTRACTION = RecipeExtraction(
    title="Bolo de cenoura",
    servings=8,
    prep_time_minutes=15,
    ingredients=[IngredientExtraction(name="cenoura", quantity="3", unit="unidades")],
    steps=[StepExtraction(order=1, text="Bata tudo e leve ao forno.")],
)


async def _stub_scrape(url: str) -> str:
    return "texto extraído da página"


async def _stub_extract(text: str) -> RecipeExtraction:
    return FAKE_EXTRACTION


async def _override_get_db_session() -> AsyncGenerator:
    """Build a session bound to the test database, fresh at request time.

    TestClient drives the ASGI app in its own thread/event loop (an anyio
    blocking portal), so a session created ahead of time in the
    pytest-asyncio test loop can't be reused here — it must be created
    inside this generator, in whichever loop actually calls it.
    """
    engine = create_async_engine(get_settings().test_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_database_after_test() -> AsyncGenerator[None, None]:
    """The app manages its own per-request sessions here (see above), so
    cleanup runs directly against the test database instead of a session
    object shared with the test."""
    yield
    engine = create_async_engine(get_settings().test_database_url)
    async with engine.begin() as connection:
        await connection.execute(delete(Recipe))
    await engine.dispose()


@pytest.fixture
def make_client() -> Callable[..., TestClient]:
    """Factory fixture: a TestClient with the recipe service's scrape/extract
    replaced by the given stubs (defaults to a successful extraction)."""

    def _make(*, scrape: Callable = _stub_scrape, extract: Callable = _stub_extract) -> TestClient:
        def override_get_recipe_service(
            session=Depends(get_db_session),
        ) -> RecipeService:
            return RecipeService(session, scrape=scrape, extract=extract)

        app.dependency_overrides[get_db_session] = _override_get_db_session
        app.dependency_overrides[get_recipe_service] = override_get_recipe_service
        return TestClient(app)

    yield _make

    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    """The common case: a client with default (successful) stubs."""
    return make_client()


def test_given_a_valid_url_when_posting_a_recipe_then_it_is_created_and_returned(
    client: TestClient,
) -> None:
    """Given a reachable URL with recipe content, when POSTed to
    /api/recipes, then the extracted recipe is persisted and returned."""
    response = client.post("/api/recipes", json={"url": "https://example.com/receita"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Bolo de cenoura"
    assert body["servings"] == 8
    assert body["ingredients"][0]["name"] == "cenoura"
    assert uuid.UUID(body["id"])


def test_given_persisted_recipes_when_listing_then_returns_them(client: TestClient) -> None:
    """Given a recipe was created, when listing recipes, then it appears in
    the results."""
    client.post("/api/recipes", json={"url": "https://example.com/receita"})

    response = client.get("/api/recipes")

    assert response.status_code == 200
    titles = [recipe["title"] for recipe in response.json()]
    assert "Bolo de cenoura" in titles


def test_given_a_persisted_recipe_when_fetched_by_id_then_it_is_returned(
    client: TestClient,
) -> None:
    """Given a recipe was created, when fetched by its id, then the full
    recipe is returned."""
    created = client.post("/api/recipes", json={"url": "https://example.com/receita"}).json()

    response = client.get(f"/api/recipes/{created['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Bolo de cenoura"


def test_given_no_recipe_with_the_given_id_when_fetched_then_returns_not_found(
    client: TestClient,
) -> None:
    """Given no recipe exists with a given id, when fetched, then a 404
    with a Portuguese message is returned."""
    response = client.get(f"/api/recipes/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Receita não encontrada."


def test_given_a_persisted_recipe_when_updated_then_the_changes_are_saved(
    client: TestClient,
) -> None:
    """Given a recipe was created, when updated with a new title, then the
    change is persisted and returned."""
    created = client.post("/api/recipes", json={"url": "https://example.com/receita"}).json()

    response = client.patch(
        f"/api/recipes/{created['id']}", json={"title": "Bolo de cenoura com cobertura"}
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Bolo de cenoura com cobertura"


def test_given_no_recipe_with_the_given_id_when_updated_then_returns_not_found(
    client: TestClient,
) -> None:
    """Given no recipe exists with a given id, when an update is attempted,
    then a 404 with a Portuguese message is returned."""
    response = client.patch(f"/api/recipes/{uuid.uuid4()}", json={"title": "Não existe"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Receita não encontrada."


def test_given_a_persisted_recipe_when_deleted_then_it_no_longer_exists(
    client: TestClient,
) -> None:
    """Given a recipe was created, when deleted, then it can no longer be
    fetched."""
    created = client.post("/api/recipes", json={"url": "https://example.com/receita"}).json()

    delete_response = client.delete(f"/api/recipes/{created['id']}")
    get_response = client.get(f"/api/recipes/{created['id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_given_no_recipe_with_the_given_id_when_deleted_then_returns_not_found(
    client: TestClient,
) -> None:
    """Given no recipe exists with a given id, when a deletion is
    attempted, then a 404 with a Portuguese message is returned."""
    response = client.delete(f"/api/recipes/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Receita não encontrada."


def test_given_the_source_page_is_unreachable_when_posting_then_returns_a_portuguese_error(
    make_client: Callable[..., TestClient],
) -> None:
    """Given the scraper cannot reach the source URL, when POSTed to
    /api/recipes, then a 422 with a Portuguese, user-facing message is
    returned."""

    async def failing_scrape(url: str) -> str:
        raise UnreachableUrlError("boom")

    client = make_client(scrape=failing_scrape)

    response = client.post("/api/recipes", json={"url": "https://example.com/receita"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Não foi possível acessar o link informado."


def test_given_the_ai_provider_is_unavailable_when_posting_then_returns_a_portuguese_error(
    make_client: Callable[..., TestClient],
) -> None:
    """Given the AI provider request fails, when POSTed to /api/recipes,
    then a 503 with a Portuguese, user-facing message is returned."""

    async def failing_extract(text: str) -> RecipeExtraction:
        raise AIRequestError("boom")

    client = make_client(extract=failing_extract)

    response = client.post("/api/recipes", json={"url": "https://example.com/receita"})

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "O serviço de extração por IA está indisponível no momento. Tente novamente em instantes."
    )
