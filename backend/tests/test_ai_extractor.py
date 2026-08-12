"""Specifications for AI-based recipe extraction via OpenRouter.

Sends the page text scraped in a previous layer to the configured model and
validates the response against the RecipeExtractionOutcome schema — the AI
either returns a recipe, or explicitly signals that the source text isn't
one. All tests mock the HTTP layer (httpx.MockTransport) — no real
OpenRouter calls are made.
"""

import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.services.ai_extractor import (
    AIRequestError,
    MalformedAIResponseError,
    NotARecipeError,
    extract_recipe,
)

VALID_RECIPE_JSON = {
    "title": "Bolo de cenoura",
    "description": None,
    "image_url": None,
    "prep_time_minutes": 15,
    "cook_time_minutes": 40,
    "total_time_minutes": 55,
    "servings": 8,
    "ingredients": [
        {"name": "cenoura", "quantity": "3", "unit": "unidades", "notes": None},
    ],
    "steps": [
        {"order": 1, "text": "Bata tudo no liquidificador."},
    ],
    "tags": None,
}

VALID_EXTRACTION_JSON = json.dumps({"is_recipe": True, "reason": None, "recipe": VALID_RECIPE_JSON})

NOT_A_RECIPE_JSON = json.dumps(
    {
        "is_recipe": False,
        "reason": "A página é uma listagem de categorias, sem ingredientes ou modo de preparo.",
        "recipe": None,
    }
)


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


async def test_given_a_valid_ai_response_when_extracting_then_returns_the_parsed_recipe() -> None:
    """Given the model returns is_recipe=true with a recipe matching the
    schema, when extracting, then a validated RecipeExtraction is
    returned."""
    client = _client_returning(_chat_completion_response(content=VALID_EXTRACTION_JSON))

    extraction = await extract_recipe("texto da receita...", client=client)

    assert extraction.title == "Bolo de cenoura"
    assert extraction.servings == 8
    assert extraction.ingredients[0].name == "cenoura"
    assert extraction.steps[0].text == "Bata tudo no liquidificador."


async def test_given_the_model_reports_the_text_is_not_a_recipe_when_extracting_then_raises_not_a_recipe_error() -> (
    None
):
    """Given the model returns is_recipe=false (e.g. the page is a listing
    or article with no ingredients/instructions), when extracting, then a
    NotARecipeError is raised instead of an empty or partial recipe being
    returned."""
    client = _client_returning(_chat_completion_response(content=NOT_A_RECIPE_JSON))

    with pytest.raises(NotARecipeError):
        await extract_recipe("texto de uma página qualquer...", client=client)


async def test_given_is_recipe_true_but_no_recipe_data_when_extracting_then_raises_malformed_ai_response_error() -> (
    None
):
    """Given the model contradicts itself (is_recipe=true but no recipe
    data included), when extracting, then a MalformedAIResponseError is
    raised — this is a broken response, not a legitimate "not a recipe"
    signal, so it must not be reported to the user as one."""
    contradictory_json = json.dumps({"is_recipe": True, "reason": None, "recipe": None})
    client = _client_returning(_chat_completion_response(content=contradictory_json))

    with pytest.raises(MalformedAIResponseError):
        await extract_recipe("texto da receita...", client=client)


async def test_given_malformed_json_when_extracting_then_raises_malformed_ai_response_error() -> (
    None
):
    """Given the model returns text that is not valid JSON, when extracting,
    then a MalformedAIResponseError is raised."""
    client = _client_returning(_chat_completion_response(content="isso não é um JSON"))

    with pytest.raises(MalformedAIResponseError):
        await extract_recipe("texto da receita...", client=client)


async def test_given_json_missing_required_fields_when_extracting_then_raises_malformed_ai_response_error() -> (
    None
):
    """Given the model returns JSON that doesn't match the outcome schema
    (e.g. missing `is_recipe`), when extracting, then a
    MalformedAIResponseError is raised."""
    incomplete_json = json.dumps({"recipe": {"title": "Bolo de cenoura"}})
    client = _client_returning(_chat_completion_response(content=incomplete_json))

    with pytest.raises(MalformedAIResponseError):
        await extract_recipe("texto da receita...", client=client)


async def test_given_a_recipe_with_empty_ingredients_when_extracting_then_raises_malformed_ai_response_error() -> (
    None
):
    """Given the model reports is_recipe=true but the recipe itself has no
    ingredients (a self-contradictory or buggy response), when extracting,
    then a MalformedAIResponseError is raised — the RecipeExtraction schema
    itself refuses an empty ingredients list, so this can never slip
    through as a "valid" recipe."""
    broken_recipe = {**VALID_RECIPE_JSON, "ingredients": []}
    broken_json = json.dumps({"is_recipe": True, "reason": None, "recipe": broken_recipe})
    client = _client_returning(_chat_completion_response(content=broken_json))

    with pytest.raises(MalformedAIResponseError):
        await extract_recipe("texto da receita...", client=client)


async def test_given_the_model_refuses_when_extracting_then_raises_malformed_ai_response_error() -> (
    None
):
    """Given the model declines to answer (refusal), when extracting, then
    a MalformedAIResponseError is raised instead of an empty recipe."""
    client = _client_returning(
        _chat_completion_response(content=None, refusal="I can't help with that.")
    )

    with pytest.raises(MalformedAIResponseError):
        await extract_recipe("texto da receita...", client=client)


async def test_given_the_request_fails_when_extracting_then_raises_ai_request_error() -> None:
    """Given the request to OpenRouter fails outright (network error), when
    extracting, then an AIRequestError is raised."""
    client = _failing_client(httpx.ConnectError("connection refused"))

    with pytest.raises(AIRequestError):
        await extract_recipe("texto da receita...", client=client)
