"""Pydantic schemas for the recipe domain — the AI extraction contract and
the public API request/response bodies.

Every free-text field carries a max_length. The columns behind them are
unbounded Text/JSONB, so without these a single PATCH (or a hostile AI
response) could store tens of megabytes per request and fill the database
disk. The caps are far above any real recipe and only exist to refuse abuse.
"""

import uuid
from datetime import datetime
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# Generous caps: a real recipe is nowhere near these, so legitimate content
# always fits and only abuse is refused.
_TITLE_MAX = 500
_DESCRIPTION_MAX = 5_000
_NAME_MAX = 500
_QUANTITY_MAX = 100
_UNIT_MAX = 100
_NOTES_MAX = 1_000
_STEP_MAX = 5_000
_URL_MAX = 2_083
_TAG_MAX = 100
_LIST_MAX = 200


def _clean_http_url_or_none(value: str | None) -> str | None:
    """Return `value` only if it is a plain http(s) URL, else None.

    Used for the AI-provided image_url: the model reads attacker-controlled
    pages, so a `javascript:` or `data:` value must never be stored verbatim
    and handed back to a client. A bad value is dropped (None) rather than
    failing the whole extraction — the recipe is still worth saving without it.
    """
    if value is None:
        return None
    value = value.strip()
    if len(value) > _URL_MAX:
        return None
    scheme = urlsplit(value).scheme.lower()
    return value if scheme in ("http", "https") else None


class IngredientExtraction(BaseModel):
    """A single ingredient line, as extracted from a recipe's source text."""

    name: str = Field(max_length=_NAME_MAX)
    quantity: str | None = Field(
        default=None,
        max_length=_QUANTITY_MAX,
        description="Amount as written in the source, e.g. '2 xícaras'.",
    )
    unit: str | None = Field(
        default=None, max_length=_UNIT_MAX, description="Unit of measurement, if any."
    )
    notes: str | None = Field(
        default=None,
        max_length=_NOTES_MAX,
        description="Extra detail, e.g. 'picado' or 'opcional'.",
    )


class StepExtraction(BaseModel):
    """A single step of the recipe's method, in the order it should be followed."""

    order: int
    text: str = Field(max_length=_STEP_MAX)


class RecipeExtraction(BaseModel):
    """Structured recipe data extracted from a source page's text by the AI.

    Title, ingredients and steps are required to be non-empty: a page with
    none of those isn't a recipe, and the app must never store one that
    looks like it is but has nothing in it (see RecipeExtractionOutcome,
    which is how the AI is expected to signal "this isn't a recipe" instead
    of producing an empty one of these).
    """

    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    description: str | None = Field(default=None, max_length=_DESCRIPTION_MAX)
    image_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[IngredientExtraction] = Field(min_length=1, max_length=_LIST_MAX)
    steps: list[StepExtraction] = Field(min_length=1, max_length=_LIST_MAX)
    tags: list[Annotated[str, Field(max_length=_TAG_MAX)]] | None = Field(
        default=None, max_length=_LIST_MAX
    )

    @field_validator("image_url")
    @classmethod
    def _sanitize_image_url(cls, value: str | None) -> str | None:
        # AI output: drop anything that isn't a plain http(s) URL instead of
        # storing (and later serving) a javascript:/data: value.
        return _clean_http_url_or_none(value)


class RecipeExtractionOutcome(BaseModel):
    """The AI's full response to a recipe-extraction request.

    Wraps RecipeExtraction with an explicit self-assessment so the model
    has a correct way to represent "the given text isn't a recipe" (no
    identifiable ingredients or preparation steps) instead of being forced
    to either invent content or produce an empty RecipeExtraction that
    can't be persisted anyway.
    """

    is_recipe: bool
    reason: str | None = Field(
        default=None,
        description="Brief reason when is_recipe is false, e.g. 'this is a category "
        "listing page, not a recipe'.",
    )
    recipe: RecipeExtraction | None = Field(
        default=None, description="The extracted recipe. Present only when is_recipe is true."
    )


class CreateRecipeRequest(BaseModel):
    """Request body for POST /api/recipes."""

    # HttpUrl already caps the length at 2083 and restricts the scheme to
    # http(s) with a real host. It does NOT reject private addresses, though —
    # the SSRF guard in the scraper/video door does that at fetch time.
    url: HttpUrl


class RecipeResponse(BaseModel):
    """Response body representing a persisted recipe."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # Null when the recipe came from uploaded images — `source_type` says
    # which of the two it was, so a null never has to be interpreted.
    source_url: str | None = None
    source_type: str
    title: str
    description: str | None = None
    image_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[IngredientExtraction]
    steps: list[StepExtraction]
    tags: list[str] | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    # ISO 639-1 code of the language the recipe was originally in (e.g.
    # "en"), or null when it was already Portuguese — see Recipe.source_language.
    source_language: str | None = None
    created_at: datetime
    updated_at: datetime


class UpdateRecipeRequest(BaseModel):
    """Request body for PATCH /api/recipes/{id}.

    Every field is optional — only the ones explicitly sent by the client
    are applied (see the `exclude_unset` usage in the route handler).
    """

    title: str | None = Field(default=None, min_length=1, max_length=_TITLE_MAX)
    description: str | None = Field(default=None, max_length=_DESCRIPTION_MAX)
    image_url: str | None = Field(default=None, max_length=_URL_MAX)
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[IngredientExtraction] | None = Field(
        default=None, min_length=1, max_length=_LIST_MAX
    )
    steps: list[StepExtraction] | None = Field(default=None, min_length=1, max_length=_LIST_MAX)
    tags: list[Annotated[str, Field(max_length=_TAG_MAX)]] | None = Field(
        default=None, max_length=_LIST_MAX
    )

    @field_validator("image_url")
    @classmethod
    def _reject_non_http_image_url(cls, value: str | None) -> str | None:
        # User-supplied edit: reject a non-http(s) URL outright (422) rather
        # than silently dropping it, so a bad value is visible feedback.
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        scheme = urlsplit(value).scheme.lower()
        if scheme not in ("http", "https"):
            raise ValueError("image_url must be an http or https link")
        return value
