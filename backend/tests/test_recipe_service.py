"""Specifications for RecipeService, which orchestrates source reading, AI
extraction, and persistence for the recipe creation flow.

A recipe can come from a link (scraped) or from uploaded photos
(transcribed); both converge on the same extraction and persistence, and a
saved recipe is the same kind of thing either way.

Reading and AI extraction are stubbed here — they have their own test
suites (test_scraper.py, test_image_transcriber.py, test_ai_extractor.py);
this file specifies the orchestration itself, run against the real test
database.
"""

from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.recipe import IngredientExtraction, RecipeExtraction, StepExtraction
from app.services.ai_extractor import AIRequestError, NotARecipeError
from app.services.image_transcriber import UnreadableImageError
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


async def _stub_transcribe(images: Sequence[bytes]) -> str:
    return "texto transcrito das fotos"


async def test_given_a_url_when_creating_a_recipe_then_it_is_scraped_extracted_and_persisted(
    db_session: AsyncSession,
) -> None:
    """Given a URL, when creating a recipe from it, then the page is
    scraped, the text is sent for AI extraction, and the result is
    persisted with the source URL, extracted fields, and AI metadata."""
    service = RecipeService(db_session, scrape=_stub_scrape, extract=_stub_extract)

    recipe = await service.create_from_url("https://example.com/receita")

    assert recipe.id is not None
    assert recipe.source_url == "https://example.com/receita"
    assert recipe.title == "Bolo de cenoura"
    assert recipe.servings == 8
    assert recipe.ingredients[0]["name"] == "cenoura"
    assert recipe.steps[0]["text"] == "Bata tudo e leve ao forno."
    assert recipe.raw_extracted_text == "texto extraído da página"
    assert recipe.source_type == "link"
    assert recipe.ai_provider == "openrouter"
    assert recipe.ai_model


async def test_given_photos_of_a_recipe_when_creating_a_recipe_then_they_are_transcribed_extracted_and_persisted(
    db_session: AsyncSession,
) -> None:
    """Given photos of a recipe, when creating a recipe from them, then they
    are transcribed, that text goes through the same AI extraction the link
    flow uses, and the result is persisted with no source URL — the photos
    themselves are not kept, so the transcription is what remains of them."""
    service = RecipeService(db_session, transcribe=_stub_transcribe, extract=_stub_extract)

    recipe = await service.create_from_images([b"foto-pagina-1", b"foto-pagina-2"])

    assert recipe.id is not None
    assert recipe.source_url is None
    assert recipe.source_type == "image"
    assert recipe.title == "Bolo de cenoura"
    assert recipe.ingredients[0]["name"] == "cenoura"
    assert recipe.steps[0]["text"] == "Bata tudo e leve ao forno."
    assert recipe.raw_extracted_text == "texto transcrito das fotos"
    assert recipe.ai_provider == "openrouter"
    assert recipe.ai_model


async def test_given_the_photos_cannot_be_read_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the vision model gets no usable text out of the photos, when
    creating a recipe, then UnreadableImageError propagates unchanged and
    nothing is persisted."""

    async def unreadable_transcribe(images: Sequence[bytes]) -> str:
        raise UnreadableImageError("boom")

    service = RecipeService(db_session, transcribe=unreadable_transcribe, extract=_stub_extract)

    with pytest.raises(UnreadableImageError):
        await service.create_from_images([b"foto-borrada"])


async def test_given_the_photos_are_not_a_recipe_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the photos read fine but describe no recipe, when creating a
    recipe, then NotARecipeError propagates unchanged — the same rejection
    the link flow gets, since both share the extraction step."""

    async def not_a_recipe_extract(text: str) -> RecipeExtraction:
        raise NotARecipeError("a foto não tem ingredientes nem modo de preparo")

    service = RecipeService(db_session, transcribe=_stub_transcribe, extract=not_a_recipe_extract)

    with pytest.raises(NotARecipeError):
        await service.create_from_images([b"foto-de-um-cardapio"])


async def test_given_the_source_page_is_unreachable_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the scraper cannot reach the source URL, when creating a
    recipe, then UnreachableUrlError propagates unchanged — the API layer
    is responsible for translating it into a user-facing response."""

    async def failing_scrape(url: str) -> str:
        raise UnreachableUrlError("boom")

    service = RecipeService(db_session, scrape=failing_scrape, extract=_stub_extract)

    with pytest.raises(UnreachableUrlError):
        await service.create_from_url("https://example.com/receita")


async def test_given_the_ai_request_fails_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the AI extraction request fails, when creating a recipe, then
    AIRequestError propagates unchanged — the API layer is responsible for
    translating it into a user-facing response."""

    async def failing_extract(text: str) -> RecipeExtraction:
        raise AIRequestError("boom")

    service = RecipeService(db_session, scrape=_stub_scrape, extract=failing_extract)

    with pytest.raises(AIRequestError):
        await service.create_from_url("https://example.com/receita")


async def test_given_the_source_is_not_a_recipe_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the AI determines the source text isn't a recipe, when
    creating a recipe, then NotARecipeError propagates unchanged and
    nothing is persisted — the API layer is responsible for translating it
    into a user-facing response."""

    async def not_a_recipe_extract(text: str) -> RecipeExtraction:
        raise NotARecipeError("a página não tem ingredientes nem modo de preparo")

    service = RecipeService(db_session, scrape=_stub_scrape, extract=not_a_recipe_extract)

    with pytest.raises(NotARecipeError):
        await service.create_from_url("https://example.com/nao-e-receita")
