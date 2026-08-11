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
    """Structured recipe data extracted from a source page's text by the AI."""

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


class CreateRecipeRequest(BaseModel):
    """Request body for POST /api/recipes."""

    url: HttpUrl


class RecipeResponse(BaseModel):
    """Response body representing a persisted recipe."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_url: str
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

    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[IngredientExtraction] | None = None
    steps: list[StepExtraction] | None = None
    tags: list[str] | None = None
