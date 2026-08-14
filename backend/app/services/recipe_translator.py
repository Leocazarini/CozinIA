"""Detects the language a recipe was extracted in and, when it isn't
Portuguese, translates every reader-facing field to Brazilian Portuguese and
converts its measurements to the metric units used in Brazil — the same step
regardless of whether the recipe arrived as a link, a photo, or a video link,
since all three converge on the same RecipeExtraction before this runs (see
recipe_service.py).

Detection happens locally, offline, via langdetect (`detect_language`) — the
common case for this app is a recipe already in Portuguese, and that case
should never reach the AI. Translation (`translate_recipe`) reuses the same
OpenRouter chat-completions setup as ai_extractor.py, asking for the same
RecipeExtraction shape back so nothing downstream has to change, but the AI
is trusted only for prose: every number (times, servings, image_url, step
order) is carried over from the original untouched, and every ingredient's
quantity/unit goes through unit_converter's deterministic math whenever its
original unit is one it recognises — see _merge_translation.

`translate_if_needed` is the entry point recipe_service.py actually calls.
It is deliberately best-effort: a recipe that reaches this point already
survived extraction, and losing it over a translation hiccup would throw
away something real over what is, at worst, a cosmetic failure. A failed
translation call is logged and the recipe is kept in its original language
rather than raising.
"""

import logging
from dataclasses import dataclass

from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException
from openai import (
    AsyncOpenAI,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    OpenAIError,
)
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.recipe import IngredientExtraction, RecipeExtraction, StepExtraction
from app.services.unit_converter import convert_measurement

logger = logging.getLogger(__name__)

# Duplicated from ai_extractor.py and the other services that build an
# OpenRouter client, which already carry a copy each — see the note in
# video_transcriber.py (chore/extract-openrouter-client) for why that isn't
# fixed opportunistically here.
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Cap how long a translation may hold a worker. Without it the OpenAI SDK's
# 600-second default applies, which — chained after extraction's own call —
# could pin one worker for twenty minutes on a single request.
_AI_REQUEST_TIMEOUT_SECONDS = 120.0

# langdetect picks a random seed per process unless told not to — fixing it
# makes detect() deterministic, which matters for tests and for not flapping
# between "translate" and "don't" on borderline text.
DetectorFactory.seed = 0

PORTUGUESE_LANGUAGE_CODE = "pt"

_SYSTEM_PROMPT = (
    "You translate a structured recipe into Brazilian Portuguese (pt-BR).\n\n"
    "Translate every reader-facing text field — title, description, each ingredient's name "
    "and notes, every step's text, and any tags — into natural, idiomatic Brazilian "
    "Portuguese, the way a Brazilian cooking site or cookbook would phrase it.\n\n"
    "Convert every measurement to the metric units used in Brazil: grams (g) or kilograms "
    "(kg) for weight, milliliters (ml) or liters (L) for volume, Celsius (°C) for temperature, "
    "centimeters (cm) for length — regardless of what system the source used (US customary, "
    "imperial, or any other). This applies both to an ingredient's quantity/unit and to any "
    "measurement mentioned inside a step's text (an oven temperature, a pan size). Leave "
    "count-based quantities — eggs, cloves, slices, units, a pinch — unchanged; only convert "
    "quantities that are actual measurements.\n\n"
    "Preserve the recipe's structure exactly: the same number of ingredients and steps, in "
    "the same order. Never add, remove, merge or reorder items, and never invent content that "
    "wasn't in the source — a translation changes language and units, nothing else.\n\n"
    "Round converted values to a sensible cooking precision instead of reporting false "
    "precision from the raw conversion factor."
)


class TranslationError(Exception):
    """Base exception for recipe-translation failures."""


class TranslationRequestError(TranslationError):
    """Raised when the request to the AI provider itself fails."""


class MalformedTranslationResponseError(TranslationError):
    """Raised when the AI's response can't be parsed into a RecipeExtraction,
    or doesn't preserve the original's number of ingredients/steps."""


@dataclass(frozen=True)
class TranslationResult:
    """The recipe `translate_if_needed` returns, plus the language it was
    found in.

    `source_language` is None in both cases where `extraction` comes back
    exactly as it went in: the recipe was already Portuguese, or there
    wasn't enough text to tell. When translation was attempted but failed,
    `source_language` is still set — it's real information (the recipe *is*
    in that language) even though translating it didn't work this time.
    """

    extraction: RecipeExtraction
    source_language: str | None


def detect_language(extraction: RecipeExtraction) -> str | None:
    """Return the ISO 639-1 code langdetect guesses for the recipe's text,
    or None when there isn't enough text to tell.

    Runs on the extraction's own fields — title, description, ingredient
    names, step text — not the raw source text: that's the content
    translation actually needs to reach, already filtered of page furniture
    (nav, ads, comments) by the extraction step that produced it.
    """
    sample = "\n".join(_text_fields(extraction))
    try:
        return detect(sample)
    except LangDetectException:
        return None


def _text_fields(extraction: RecipeExtraction) -> list[str]:
    fields = [extraction.title, extraction.description or ""]
    fields.extend(ingredient.name for ingredient in extraction.ingredients)
    fields.extend(step.text for step in extraction.steps)
    return [field for field in fields if field]


async def translate_if_needed(
    extraction: RecipeExtraction, *, client: AsyncOpenAI | None = None
) -> TranslationResult:
    """Detect `extraction`'s language and translate it to Portuguese (with
    its measurements converted) if it isn't already. See the module
    docstring for why a failed translation call is swallowed rather than
    raised.
    """
    language = detect_language(extraction)
    if language is None or language == PORTUGUESE_LANGUAGE_CODE:
        return TranslationResult(extraction=extraction, source_language=None)

    try:
        translated = await translate_recipe(extraction, client=client)
    except TranslationError as error:
        logger.warning(
            "Recipe translation from %r failed, keeping the original: %s", language, error
        )
        return TranslationResult(extraction=extraction, source_language=language)

    return TranslationResult(extraction=translated, source_language=language)


async def translate_recipe(
    extraction: RecipeExtraction, *, client: AsyncOpenAI | None = None
) -> RecipeExtraction:
    """Translate `extraction` to Brazilian Portuguese and convert its
    measurements, and return the result.

    Raises TranslationRequestError if the request to the provider fails, and
    MalformedTranslationResponseError if the response can't be parsed into a
    RecipeExtraction or doesn't keep the same number of ingredients and
    steps as the original.

    `client` is exposed so tests can inject one backed by an
    httpx.MockTransport instead of hitting the real network.
    """
    settings = get_settings()
    active_client = client if client is not None else _build_client()

    try:
        completion = await active_client.chat.completions.parse(
            model=settings.ai_translation_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": extraction.model_dump_json()},
            ],
            response_format=RecipeExtraction,
            timeout=_AI_REQUEST_TIMEOUT_SECONDS,
        )
    except (LengthFinishReasonError, ContentFilterFinishReasonError) as error:
        raise MalformedTranslationResponseError(f"AI response was not usable: {error}") from error
    except ValidationError as error:
        raise MalformedTranslationResponseError(
            f"AI response did not match the recipe schema: {error}"
        ) from error
    except OpenAIError as error:
        raise TranslationRequestError(f"OpenRouter translation request failed: {error}") from error

    message = completion.choices[0].message
    if message.parsed is None:
        reason = message.refusal or "empty response"
        raise MalformedTranslationResponseError(f"AI did not return a usable translation: {reason}")

    return _merge_translation(extraction, message.parsed)


def _build_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(base_url=_OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)


def _merge_translation(
    original: RecipeExtraction, translated: RecipeExtraction
) -> RecipeExtraction:
    """Combine the two: translated prose from the AI's response, but every
    number, the image, and every unit conversion computed deterministically
    from the original — the AI never gets the final say on those.

    Raises MalformedTranslationResponseError if the AI changed how many
    ingredients or steps there are — the one thing a translation must never
    do.
    """
    if len(translated.ingredients) != len(original.ingredients):
        raise MalformedTranslationResponseError(
            f"translation returned {len(translated.ingredients)} ingredients, "
            f"expected {len(original.ingredients)}"
        )
    if len(translated.steps) != len(original.steps):
        raise MalformedTranslationResponseError(
            f"translation returned {len(translated.steps)} steps, expected {len(original.steps)}"
        )

    ingredients = [
        _merge_ingredient(original_ingredient, translated_ingredient)
        for original_ingredient, translated_ingredient in zip(
            original.ingredients, translated.ingredients, strict=True
        )
    ]
    steps = [
        StepExtraction(order=original_step.order, text=translated_step.text)
        for original_step, translated_step in zip(original.steps, translated.steps, strict=True)
    ]

    return RecipeExtraction(
        title=translated.title,
        description=translated.description,
        image_url=original.image_url,
        prep_time_minutes=original.prep_time_minutes,
        cook_time_minutes=original.cook_time_minutes,
        total_time_minutes=original.total_time_minutes,
        servings=original.servings,
        ingredients=ingredients,
        steps=steps,
        tags=translated.tags,
    )


def _merge_ingredient(
    original: IngredientExtraction, translated: IngredientExtraction
) -> IngredientExtraction:
    """Prose (name, notes) always comes from the translation. The
    quantity/unit come from converting the *original* deterministically —
    unless its unit isn't one unit_converter recognises, in which case its
    own (unchanged) output signals that, and the AI's translation of the
    quantity/unit is trusted instead of being thrown away."""
    quantity, unit = convert_measurement(original.quantity, original.unit)
    if (quantity, unit) == (original.quantity, original.unit):
        quantity, unit = translated.quantity, translated.unit
    return IngredientExtraction(
        name=translated.name, quantity=quantity, unit=unit, notes=translated.notes
    )
