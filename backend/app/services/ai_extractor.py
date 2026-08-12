"""Extracts structured recipe data from raw page text using an LLM via OpenRouter.

OpenRouter exposes an OpenAI-compatible API, so the official `openai` SDK is
used as the client, pointed at OpenRouter's base URL. Swapping the
underlying model/provider is a matter of changing the AI_MODEL setting —
this module never needs to change.
"""

import logging

from openai import (
    AsyncOpenAI,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    OpenAIError,
)
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.recipe import RecipeExtraction, RecipeExtractionOutcome

logger = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_SYSTEM_PROMPT = (
    "You extract recipe data from webpage text. Read the provided text and decide whether it "
    "actually describes a recipe with identifiable ingredients and preparation steps.\n\n"
    "If it does: set is_recipe to true and fill in recipe with the title, description, timing, "
    "servings, ingredients and steps as structured data. Only use information present in the "
    "text — never invent ingredients, quantities, or steps, and never fill recipe with "
    "placeholder or guessed content just to satisfy the schema.\n\n"
    "If it does not — e.g. the text is a category/listing page, an article, a product page, or "
    "a recipe page whose ingredients/instructions aren't present in the given text — set "
    "is_recipe to false, leave recipe unset, and briefly say why in reason."
)


class AIExtractionError(Exception):
    """Base exception for AI-based recipe extraction failures."""


class AIRequestError(AIExtractionError):
    """Raised when the request to the AI provider itself fails."""


class MalformedAIResponseError(AIExtractionError):
    """Raised when the AI response cannot be parsed into a RecipeExtractionOutcome, or is
    internally inconsistent (e.g. reports a recipe but includes none)."""


class NotARecipeError(AIExtractionError):
    """Raised when the AI determines the source text isn't an actual recipe
    (no identifiable ingredients or preparation steps)."""


def _build_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(base_url=_OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)


async def extract_recipe(text: str, *, client: AsyncOpenAI | None = None) -> RecipeExtraction:
    """Send scraped page text to the configured OpenRouter model and return
    a validated RecipeExtraction.

    Raises AIRequestError if the request to the provider fails,
    MalformedAIResponseError if the response cannot be parsed into a
    RecipeExtractionOutcome (invalid JSON, missing fields, a model refusal,
    or a self-contradictory "is_recipe=true" with no recipe attached), and
    NotARecipeError if the AI determines the source text doesn't describe a
    recipe at all.

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
            response_format=RecipeExtractionOutcome,
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

    outcome = message.parsed
    if not outcome.is_recipe:
        logger.info("AI determined the source text is not a recipe: %s", outcome.reason)
        raise NotARecipeError(outcome.reason or "The AI determined this page is not a recipe.")

    if outcome.recipe is None:
        raise MalformedAIResponseError("AI reported is_recipe=true but did not include recipe data")

    return outcome.recipe
