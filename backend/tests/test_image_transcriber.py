"""Specifications for turning uploaded recipe photos into plain text via a
vision model on OpenRouter.

This is the image flow's counterpart to the scraper: it produces the text
that `extract_recipe` then structures, so the whole "is this actually a
recipe?" contract is reused untouched. All tests mock the HTTP layer
(httpx.MockTransport) — no real OpenRouter calls are made.
"""

import base64
import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.ai_extractor import AIRequestError
from app.services.image_transcriber import UnreadableImageError, transcribe_images

FIRST_PAGE = b"first-page-jpeg-bytes"
SECOND_PAGE = b"second-page-jpeg-bytes"

TRANSCRIPT = (
    "Bolo de cenoura\n\n"
    "Ingredientes:\n- 3 cenouras médias\n- 3 ovos\n- 2 xícaras de açúcar\n\n"
    "Modo de preparo:\n1. Bata a cenoura, os ovos e o açúcar no liquidificador.\n"
    "2. Leve ao forno a 180 graus por 40 minutos."
)


def _chat_completion_response(content: str | None) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "anthropic/claude-sonnet-5",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content, "refusal": None},
            }
        ],
    }


def _client_returning(content: str | None) -> tuple[AsyncOpenAI, list[dict]]:
    """A client answering with `content`, plus the list where each request
    payload it received is recorded (so tests can inspect what was sent)."""
    sent_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content))
        return httpx.Response(200, json=_chat_completion_response(content))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client), sent_payloads


def _failing_client(exception: httpx.HTTPError) -> AsyncOpenAI:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client)


def _image_parts(payload: dict) -> list[dict]:
    user_message = next(message for message in payload["messages"] if message["role"] == "user")
    return [part for part in user_message["content"] if part["type"] == "image_url"]


async def test_given_a_photo_of_a_recipe_when_transcribing_then_returns_its_text() -> None:
    """Given a legible photo of a recipe, when transcribing, then the model's
    plain-text reading of it is returned — ready to be handed to the same
    extractor the link flow uses."""
    client, _ = _client_returning(TRANSCRIPT)

    text = await transcribe_images([FIRST_PAGE], client=client)

    assert text == TRANSCRIPT


async def test_given_several_photos_when_transcribing_then_all_are_sent_in_order() -> None:
    """Given the two pages a recipe spans in a cookbook, when transcribing,
    then both images travel in the same request, in the order given — they
    are pages of one recipe, and reading them out of order would put the
    method before the ingredients."""
    client, sent_payloads = _client_returning(TRANSCRIPT)

    await transcribe_images([FIRST_PAGE, SECOND_PAGE], client=client)

    parts = _image_parts(sent_payloads[0])
    assert len(parts) == 2
    assert [_decode_data_uri(part["image_url"]["url"]) for part in parts] == [
        FIRST_PAGE,
        SECOND_PAGE,
    ]


async def test_given_photos_to_transcribe_then_the_configured_vision_model_is_used() -> None:
    """Given any transcription request, when it is sent, then it targets the
    vision model setting — not the text model used for extraction, which
    need not be able to see images at all."""
    client, sent_payloads = _client_returning(TRANSCRIPT)

    await transcribe_images([FIRST_PAGE], client=client)

    assert sent_payloads[0]["model"] == get_settings().ai_vision_model


async def test_given_a_photo_with_no_legible_text_when_transcribing_then_raises_unreadable_image_error() -> (
    None
):
    """Given a photo the model reads almost nothing out of (blurry, or not a
    document at all), when transcribing, then an UnreadableImageError is
    raised — sending a scrap of text on to the extractor would only produce
    a confusing "this isn't a recipe" further down."""
    client, _ = _client_returning("nada legível")

    with pytest.raises(UnreadableImageError):
        await transcribe_images([FIRST_PAGE], client=client)


async def test_given_the_model_returns_nothing_when_transcribing_then_raises_unreadable_image_error() -> (
    None
):
    """Given the model answers with no content at all (an empty message or a
    refusal), when transcribing, then an UnreadableImageError is raised."""
    client, _ = _client_returning(None)

    with pytest.raises(UnreadableImageError):
        await transcribe_images([FIRST_PAGE], client=client)


async def test_given_the_request_fails_when_transcribing_then_raises_ai_request_error() -> None:
    """Given the request to OpenRouter fails outright (network error), when
    transcribing, then an AIRequestError is raised — the same exception the
    text extraction flow raises, so the API layer already handles it."""
    client = _failing_client(httpx.ConnectError("connection refused"))

    with pytest.raises(AIRequestError):
        await transcribe_images([FIRST_PAGE], client=client)


def _decode_data_uri(url: str) -> bytes:
    header, _, payload = url.partition(",")
    assert header == "data:image/jpeg;base64"
    return base64.b64decode(payload)
