"""Extracts structured recipe data from raw page text using an LLM via OpenRouter.

OpenRouter exposes an OpenAI-compatible API, so the official `openai` SDK is
used as the client, pointed at OpenRouter's base URL. Swapping the
underlying model/provider is a matter of changing the AI_MODEL setting —
this module never needs to change.
"""

from openai import (
    AsyncOpenAI,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    OpenAIError,
)
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.recipe import RecipeExtraction

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_SYSTEM_PROMPT = (
    "You extract recipe data from webpage text. Read the provided text and "
    "return the recipe's title, description, timing, servings, ingredients "
    "and steps as structured data. Only use information present in the "
    "text — never invent ingredients, quantities, or steps."
)


class AIExtractionError(Exception):
    """Base exception for AI-based recipe extraction failures."""


class AIRequestError(AIExtractionError):
    """Raised when the request to the AI provider itself fails."""


class MalformedAIResponseError(AIExtractionError):
    """Raised when the AI response cannot be parsed into a RecipeExtraction."""


def _build_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(base_url=_OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)


async def extract_recipe(text: str, *, client: AsyncOpenAI | None = None) -> RecipeExtraction:
    """Send scraped page text to the configured OpenRouter model and return
    a validated RecipeExtraction.

    Raises AIRequestError if the request to the provider fails, and
    MalformedAIResponseError if the response cannot be parsed into a
    RecipeExtraction (invalid JSON, missing fields, or a model refusal).

    `client` is exposed so tests can inject one backed by an
    httpx.MockTransport instead of hitting the real network.
    """
    settings = get_settings()
    active_client = client if client is not None else _build_client()

    try:
        completion = await active_client.chat.completions.parse(
            model=settings.ai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=RecipeExtraction,
        )
    except (LengthFinishReasonError, ContentFilterFinishReasonError) as error:
        raise MalformedAIResponseError(f"AI response was not usable: {error}") from error
    except ValidationError as error:
        raise MalformedAIResponseError(
            f"AI response did not match the recipe schema: {error}"
        ) from error
    except OpenAIError as error:
        raise AIRequestError(f"OpenRouter request failed: {error}") from error

    message = completion.choices[0].message
    if message.parsed is None:
        reason = message.refusal or "empty response"
        raise MalformedAIResponseError(f"AI did not return a usable recipe: {reason}")

    return message.parsed
