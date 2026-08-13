"""Pydantic schemas for the recipe domain — the AI extraction contract and
the public API request/response bodies."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class IngredientExtraction(BaseModel):
    """A single ingredient line, as extracted from a recipe's source text."""

    name: str
    quantity: str | None = Field(
        default=None, description="Amount as written in the source, e.g. '2 xícaras'."
    )
    unit: str | None = Field(default=None, description="Unit of measurement, if any.")
    notes: str | None = Field(
        default=None, description="Extra detail, e.g. 'picado' or 'opcional'."
    )


class StepExtraction(BaseModel):
    """A single step of the recipe's method, in the order it should be followed."""

    order: int
    text: str


class RecipeExtraction(BaseModel):
    """Structured recipe data extracted from a source page's text by the AI.

    Title, ingredients and steps are required to be non-empty: a page with
    none of those isn't a recipe, and the app must never store one that
    looks like it is but has nothing in it (see RecipeExtractionOutcome,
    which is how the AI is expected to signal "this isn't a recipe" instead
    of producing an empty one of these).
    """

    title: str = Field(min_length=1)
    description: str | None = None
    image_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[IngredientExtraction] = Field(min_length=1)
    steps: list[StepExtraction] = Field(min_length=1)
    tags: list[str] | None = None


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
    created_at: datetime
    updated_at: datetime


class UpdateRecipeRequest(BaseModel):
    """Request body for PATCH /api/recipes/{id}.

    Every field is optional — only the ones explicitly sent by the client
    are applied (see the `exclude_unset` usage in the route handler).
    """

    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    image_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[IngredientExtraction] | None = Field(default=None, min_length=1)
    steps: list[StepExtraction] | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
