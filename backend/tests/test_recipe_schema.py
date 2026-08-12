"""Specifications for the recipe domain schemas' validation rules.

The app must never end up storing a "recipe" with no title, no ingredients,
or no preparation steps — a page that has none of those isn't a recipe at
all, so these are enforced as hard invariants on the schemas themselves
(the AI extraction contract and the manual-edit request), not left to
callers to check.
"""

import pytest
from pydantic import ValidationError

from app.schemas.recipe import (
    IngredientExtraction,
    RecipeExtraction,
    RecipeExtractionOutcome,
    StepExtraction,
    UpdateRecipeRequest,
)

VALID_INGREDIENT = IngredientExtraction(name="cenoura")
VALID_STEP = StepExtraction(order=1, text="Bata tudo e leve ao forno.")


def _valid_extraction_kwargs(**overrides: object) -> dict:
    defaults: dict = {
        "title": "Bolo de cenoura",
        "ingredients": [VALID_INGREDIENT],
        "steps": [VALID_STEP],
    }
    defaults.update(overrides)
    return defaults


def test_given_all_required_fields_when_building_a_recipe_extraction_then_it_succeeds() -> None:
    """Given a title, at least one ingredient and one step, when building a
    RecipeExtraction, then it succeeds."""
    extraction = RecipeExtraction(**_valid_extraction_kwargs())

    assert extraction.title == "Bolo de cenoura"


def test_given_no_title_when_building_a_recipe_extraction_then_it_is_rejected() -> None:
    """Given an empty title, when building a RecipeExtraction, then
    validation fails — a titleless record isn't a usable recipe."""
    with pytest.raises(ValidationError):
        RecipeExtraction(**_valid_extraction_kwargs(title=""))


def test_given_no_ingredients_when_building_a_recipe_extraction_then_it_is_rejected() -> None:
    """Given an empty ingredients list, when building a RecipeExtraction,
    then validation fails — the app must never store a recipe with no
    ingredients."""
    with pytest.raises(ValidationError):
        RecipeExtraction(**_valid_extraction_kwargs(ingredients=[]))


def test_given_no_steps_when_building_a_recipe_extraction_then_it_is_rejected() -> None:
    """Given an empty steps list, when building a RecipeExtraction, then
    validation fails — the app must never store a recipe with no
    preparation steps."""
    with pytest.raises(ValidationError):
        RecipeExtraction(**_valid_extraction_kwargs(steps=[]))


def test_given_is_recipe_true_with_a_recipe_when_building_an_outcome_then_it_succeeds() -> None:
    """Given is_recipe=true and a populated recipe, when building a
    RecipeExtractionOutcome, then it succeeds."""
    outcome = RecipeExtractionOutcome(
        is_recipe=True, reason=None, recipe=RecipeExtraction(**_valid_extraction_kwargs())
    )

    assert outcome.recipe is not None
    assert outcome.recipe.title == "Bolo de cenoura"


def test_given_is_recipe_false_when_building_an_outcome_then_no_recipe_is_required() -> None:
    """Given is_recipe=false and a reason, when building a
    RecipeExtractionOutcome, then it succeeds without a recipe — this is
    exactly the shape the AI is expected to return for a non-recipe page."""
    outcome = RecipeExtractionOutcome(
        is_recipe=False, reason="A página é uma listagem de produtos, não uma receita.", recipe=None
    )

    assert outcome.is_recipe is False
    assert outcome.recipe is None


def test_given_no_fields_when_building_an_update_request_then_it_succeeds() -> None:
    """Given an update request with nothing set (the common case: only some
    fields are being edited), when building it, then it succeeds — omitted
    fields must stay unconstrained so `exclude_unset` keeps working."""
    request = UpdateRecipeRequest()

    assert request.title is None
    assert request.ingredients is None
    assert request.steps is None


def test_given_an_empty_title_when_building_an_update_request_then_it_is_rejected() -> None:
    """Given the client explicitly sends an empty title, when building an
    UpdateRecipeRequest, then validation fails — same invariant as
    creation: a recipe can't be edited into having no title."""
    with pytest.raises(ValidationError):
        UpdateRecipeRequest(title="")


def test_given_an_empty_ingredients_list_when_building_an_update_request_then_it_is_rejected() -> (
    None
):
    """Given the client explicitly sends an empty ingredients list, when
    building an UpdateRecipeRequest, then validation fails — a manual edit
    can't wipe out all ingredients any more than the AI extraction can skip
    them."""
    with pytest.raises(ValidationError):
        UpdateRecipeRequest(ingredients=[])


def test_given_an_empty_steps_list_when_building_an_update_request_then_it_is_rejected() -> None:
    """Given the client explicitly sends an empty steps list, when building
    an UpdateRecipeRequest, then validation fails."""
    with pytest.raises(ValidationError):
        UpdateRecipeRequest(steps=[])
