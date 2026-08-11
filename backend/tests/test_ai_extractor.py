"""Specifications for AI-based recipe extraction via OpenRouter.

Sends the page text scraped in a previous layer to the configured model and
validates the response against the RecipeExtraction schema. All tests mock
the HTTP layer (httpx.MockTransport) — no real OpenRouter calls are made.
"""

import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.services.ai_extractor import (
    AIRequestError,
    MalformedAIResponseError,
    extract_recipe,
)

VALID_EXTRACTION_JSON = json.dumps(
    {
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
    """Given the model returns JSON matching the recipe schema, when
    extracting, then a validated RecipeExtraction is returned."""
    client = _client_returning(_chat_completion_response(content=VALID_EXTRACTION_JSON))

    extraction = await extract_recipe("texto da receita...", client=client)

    assert extraction.title == "Bolo de cenoura"
    assert extraction.servings == 8
    assert extraction.ingredients[0].name == "cenoura"
    assert extraction.steps[0].text == "Bata tudo no liquidificador."


async def test_given_malformed_json_when_extracting_then_raises_malformed_ai_response_error() -> None:
    """Given the model returns text that is not valid JSON, when extracting,
    then a MalformedAIResponseError is raised."""
    client = _client_returning(_chat_completion_response(content="isso não é um JSON"))

    with pytest.raises(MalformedAIResponseError):
        await extract_recipe("texto da receita...", client=client)


async def test_given_json_missing_required_fields_when_extracting_then_raises_malformed_ai_response_error() -> None:
    """Given the model returns JSON that doesn't match the recipe schema
    (e.g. missing required fields), when extracting, then a
    MalformedAIResponseError is raised."""
    incomplete_json = json.dumps({"title": "Bolo de cenoura"})
    client = _client_returning(_chat_completion_response(content=incomplete_json))

    with pytest.raises(MalformedAIResponseError):
        await extract_recipe("texto da receita...", client=client)


async def test_given_the_model_refuses_when_extracting_then_raises_malformed_ai_response_error() -> None:
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
