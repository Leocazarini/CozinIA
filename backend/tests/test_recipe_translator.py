"""Specifications for recipe_translator: detecting the language a recipe was
extracted in, and — when it isn't Portuguese — translating it via OpenRouter
and converting its measurements to Brazilian metric units.

Detection is real (langdetect, no network); the AI translation call mocks
the HTTP layer (httpx.MockTransport), same as test_ai_extractor.py — no real
OpenRouter calls are made.
"""

import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.schemas.recipe import IngredientExtraction, RecipeExtraction, StepExtraction
from app.services.recipe_translator import (
    MalformedTranslationResponseError,
    TranslationRequestError,
    detect_language,
    translate_if_needed,
    translate_recipe,
)

PORTUGUESE_EXTRACTION = RecipeExtraction(
    title="Bolo de cenoura",
    description="Um bolo fofinho, fácil de fazer.",
    ingredients=[IngredientExtraction(name="cenoura", quantity="3", unit="unidades")],
    steps=[StepExtraction(order=1, text="Bata tudo no liquidificador e leve ao forno.")],
)

ENGLISH_EXTRACTION = RecipeExtraction(
    title="Classic Butter Cookies",
    description="A soft, buttery cookie the whole family loves.",
    image_url="https://example.com/cookies.jpg",
    prep_time_minutes=15,
    cook_time_minutes=12,
    total_time_minutes=27,
    servings=24,
    ingredients=[
        IngredientExtraction(name="butter", quantity="8", unit="oz", notes="softened"),
        IngredientExtraction(name="salt", quantity="1", unit="pinch"),
    ],
    steps=[
        StepExtraction(order=1, text="Beat the butter until smooth."),
        StepExtraction(order=2, text="Fold in the flour and salt."),
    ],
    tags=["dessert", "cookies"],
)

# The AI's raw response for ENGLISH_EXTRACTION. Deliberately wrong/altered on
# every field the deterministic side of translation is supposed to own —
# image_url, the time/serving numbers, the butter's own unit conversion, and
# both steps' order — so a test asserting the *original* value there proves
# translate_recipe overrode the AI rather than trusting it.
TRANSLATED_RECIPE_JSON = {
    "title": "Biscoitos Amanteigados Clássicos",
    "description": "Um biscoito macio e amanteigado que a família toda adora.",
    "image_url": "https://example.com/ALTERED.jpg",
    "prep_time_minutes": 999,
    "cook_time_minutes": 999,
    "total_time_minutes": 999,
    "servings": 999,
    "ingredients": [
        {"name": "manteiga", "quantity": "230", "unit": "g", "notes": "amolecida"},
        {"name": "sal", "quantity": "1", "unit": "pitada", "notes": None},
    ],
    "steps": [
        {"order": 99, "text": "Bata a manteiga até ficar homogênea."},
        {"order": 98, "text": "Incorpore a farinha e o sal."},
    ],
    "tags": ["sobremesa", "biscoitos"],
}


def _chat_completion_response(
    *, content: str | None = None, refusal: str | None = None, finish_reason: str = "stop"
) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "anthropic/claude-sonnet-5",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
            }
        ],
    }


def _client_returning(body: dict, status_code: int = 200) -> AsyncOpenAI:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=body)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client)


def _failing_client(exception: httpx.HTTPError) -> AsyncOpenAI:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client)


def _client_that_must_not_be_called() -> AsyncOpenAI:
    """A client whose transport blows up if it's ever asked to send a
    request — used to prove a code path never reaches the AI."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("the AI translation call should not have been made")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client)


# --- detect_language ---------------------------------------------------


def test_given_a_portuguese_recipe_when_detecting_language_then_returns_pt() -> None:
    """Given a recipe already extracted in Portuguese, when detecting its
    language, then it is identified as "pt"."""
    assert detect_language(PORTUGUESE_EXTRACTION) == "pt"


def test_given_an_english_recipe_when_detecting_language_then_returns_en() -> None:
    """Given a recipe extracted in English, when detecting its language,
    then it is identified as "en"."""
    assert detect_language(ENGLISH_EXTRACTION) == "en"


def test_given_too_little_text_to_tell_when_detecting_language_then_returns_none() -> None:
    """Given a recipe whose text is too short or numeric for detection to
    say anything, when detecting its language, then None is returned
    instead of a guess."""
    ambiguous = RecipeExtraction(
        title="123",
        ingredients=[IngredientExtraction(name="1")],
        steps=[StepExtraction(order=1, text="456")],
    )

    assert detect_language(ambiguous) is None


# --- translate_recipe ---------------------------------------------------


async def test_given_a_valid_translation_when_translating_then_prose_fields_are_translated() -> (
    None
):
    """Given the AI returns a translated recipe, when translating, then the
    title, description, ingredient names/notes, step text and tags come
    back translated."""
    client = _client_returning(_chat_completion_response(content=json.dumps(TRANSLATED_RECIPE_JSON)))

    translated = await translate_recipe(ENGLISH_EXTRACTION, client=client)

    assert translated.title == "Biscoitos Amanteigados Clássicos"
    assert translated.description == "Um biscoito macio e amanteigado que a família toda adora."
    assert translated.ingredients[0].name == "manteiga"
    assert translated.ingredients[0].notes == "amolecida"
    assert translated.steps[0].text == "Bata a manteiga até ficar homogênea."
    assert translated.steps[1].text == "Incorpore a farinha e o sal."
    assert translated.tags == ["sobremesa", "biscoitos"]


async def test_given_a_recognised_unit_when_translating_then_the_deterministic_conversion_wins() -> (
    None
):
    """Given an ingredient whose original unit the deterministic converter
    recognises (oz), when translating, then the final quantity/unit come
    from that conversion — not from whatever the AI computed on its own."""
    client = _client_returning(_chat_completion_response(content=json.dumps(TRANSLATED_RECIPE_JSON)))

    translated = await translate_recipe(ENGLISH_EXTRACTION, client=client)

    # unit_converter.convert_measurement("8", "oz") == ("227", "g") — not the
    # AI's own "230"/"g".
    assert (translated.ingredients[0].quantity, translated.ingredients[0].unit) == ("227", "g")


async def test_given_an_unrecognised_unit_when_translating_then_the_ai_translation_is_kept() -> (
    None
):
    """Given an ingredient whose original unit the deterministic converter
    doesn't recognise ("pinch"), when translating, then the AI's own
    translation of the quantity/unit is used instead of being discarded."""
    client = _client_returning(_chat_completion_response(content=json.dumps(TRANSLATED_RECIPE_JSON)))

    translated = await translate_recipe(ENGLISH_EXTRACTION, client=client)

    assert (translated.ingredients[1].quantity, translated.ingredients[1].unit) == ("1", "pitada")


async def test_given_a_translation_when_translating_then_the_original_numbers_and_image_are_kept() -> (
    None
):
    """Given the AI's response, when translating, then prep/cook/total time,
    servings and image_url are always taken from the original extraction —
    none of those need translating, and the AI never gets the final say on
    them."""
    client = _client_returning(_chat_completion_response(content=json.dumps(TRANSLATED_RECIPE_JSON)))

    translated = await translate_recipe(ENGLISH_EXTRACTION, client=client)

    assert translated.image_url == ENGLISH_EXTRACTION.image_url
    assert translated.prep_time_minutes == ENGLISH_EXTRACTION.prep_time_minutes
    assert translated.cook_time_minutes == ENGLISH_EXTRACTION.cook_time_minutes
    assert translated.total_time_minutes == ENGLISH_EXTRACTION.total_time_minutes
    assert translated.servings == ENGLISH_EXTRACTION.servings


async def test_given_a_translation_when_translating_then_step_order_comes_from_the_original() -> (
    None
):
    """Given the AI's response reorders or renumbers steps, when
    translating, then the original step order is kept and only the text is
    replaced — steps are matched by position, not trusted from the AI."""
    client = _client_returning(_chat_completion_response(content=json.dumps(TRANSLATED_RECIPE_JSON)))

    translated = await translate_recipe(ENGLISH_EXTRACTION, client=client)

    assert [step.order for step in translated.steps] == [1, 2]


async def test_given_mismatched_ingredient_counts_when_translating_then_raises_malformed_translation_response_error() -> (
    None
):
    """Given the AI's response has a different number of ingredients than
    the original, when translating, then a MalformedTranslationResponseError
    is raised — the structure must be preserved exactly."""
    broken = {**TRANSLATED_RECIPE_JSON, "ingredients": TRANSLATED_RECIPE_JSON["ingredients"][:1]}
    client = _client_returning(_chat_completion_response(content=json.dumps(broken)))

    with pytest.raises(MalformedTranslationResponseError):
        await translate_recipe(ENGLISH_EXTRACTION, client=client)


async def test_given_mismatched_step_counts_when_translating_then_raises_malformed_translation_response_error() -> (
    None
):
    """Given the AI's response has a different number of steps than the
    original, when translating, then a MalformedTranslationResponseError is
    raised."""
    broken = {**TRANSLATED_RECIPE_JSON, "steps": TRANSLATED_RECIPE_JSON["steps"][:1]}
    client = _client_returning(_chat_completion_response(content=json.dumps(broken)))

    with pytest.raises(MalformedTranslationResponseError):
        await translate_recipe(ENGLISH_EXTRACTION, client=client)


async def test_given_malformed_json_when_translating_then_raises_malformed_translation_response_error() -> (
    None
):
    """Given the model returns text that isn't valid JSON, when translating,
    then a MalformedTranslationResponseError is raised."""
    client = _client_returning(_chat_completion_response(content="isso não é um JSON"))

    with pytest.raises(MalformedTranslationResponseError):
        await translate_recipe(ENGLISH_EXTRACTION, client=client)


async def test_given_the_model_refuses_when_translating_then_raises_malformed_translation_response_error() -> (
    None
):
    """Given the model declines to answer, when translating, then a
    MalformedTranslationResponseError is raised."""
    client = _client_returning(
        _chat_completion_response(content=None, refusal="I can't help with that.")
    )

    with pytest.raises(MalformedTranslationResponseError):
        await translate_recipe(ENGLISH_EXTRACTION, client=client)


async def test_given_the_request_fails_when_translating_then_raises_translation_request_error() -> (
    None
):
    """Given the request to OpenRouter fails outright, when translating,
    then a TranslationRequestError is raised."""
    client = _failing_client(httpx.ConnectError("connection refused"))

    with pytest.raises(TranslationRequestError):
        await translate_recipe(ENGLISH_EXTRACTION, client=client)


# --- translate_if_needed -------------------------------------------------


async def test_given_a_portuguese_recipe_when_translating_if_needed_then_it_is_returned_untouched() -> (
    None
):
    """Given a recipe already in Portuguese, when running translate_if_needed,
    then the recipe is returned unchanged, with no source language recorded,
    and the AI is never called."""
    client = _client_that_must_not_be_called()

    result = await translate_if_needed(PORTUGUESE_EXTRACTION, client=client)

    assert result.extraction == PORTUGUESE_EXTRACTION
    assert result.source_language is None


async def test_given_a_foreign_recipe_when_translating_if_needed_then_it_is_translated() -> None:
    """Given a recipe in another language, when running translate_if_needed,
    then the translated recipe is returned along with the language it was
    detected in."""
    client = _client_returning(_chat_completion_response(content=json.dumps(TRANSLATED_RECIPE_JSON)))

    result = await translate_if_needed(ENGLISH_EXTRACTION, client=client)

    assert result.source_language == "en"
    assert result.extraction.title == "Biscoitos Amanteigados Clássicos"


async def test_given_the_translation_call_fails_when_translating_if_needed_then_the_original_is_kept(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Given a recipe in another language but the AI translation call fails,
    when running translate_if_needed, then the original (untranslated)
    recipe is returned instead of raising — a recipe that already survived
    extraction shouldn't be lost over a translation hiccup — and a warning
    is logged so the failure isn't silent."""
    client = _failing_client(httpx.ConnectError("connection refused"))

    with caplog.at_level("WARNING", logger="app.services.recipe_translator"):
        result = await translate_if_needed(ENGLISH_EXTRACTION, client=client)

    assert result.extraction == ENGLISH_EXTRACTION
    assert result.source_language == "en"
    assert "en" in caplog.text
