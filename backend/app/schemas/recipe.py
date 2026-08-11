"""Pydantic schemas for the recipe domain — the AI extraction contract."""

from pydantic import BaseModel, Field


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
