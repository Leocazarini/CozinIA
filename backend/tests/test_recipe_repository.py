"""Specifications for RecipeRepository, the persistence layer for recipes.

Runs against a real Postgres test database (see conftest.py) to validate
that JSONB columns and constraints behave as expected, not just that the
ORM mapping is syntactically correct.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Recipe
from app.repositories.recipe_repository import RecipeRepository


def _build_recipe(**overrides: object) -> Recipe:
    defaults: dict[str, object] = {
        "source_url": "https://example.com/recipe",
        "title": "Bolo de cenoura",
        "ingredients": [
            {"quantity": "3", "unit": "unidades", "name": "cenoura", "notes": None}
        ],
        "steps": [{"order": 1, "text": "Bata tudo no liquidificador."}],
    }
    defaults.update(overrides)
    return Recipe(**defaults)


async def test_given_a_new_recipe_when_created_then_it_is_persisted_with_generated_fields(
    db_session: AsyncSession,
) -> None:
    """Given a new Recipe, when created, then it gets an id and timestamps
    from the database."""
    repository = RecipeRepository(db_session)

    created = await repository.create(_build_recipe())

    assert created.id is not None
    assert created.created_at is not None
    assert created.updated_at is not None


async def test_given_a_recipe_from_a_link_when_created_then_its_source_type_defaults_to_link(
    db_session: AsyncSession,
) -> None:
    """Given a recipe created without an explicit source_type, when
    persisted, then the database defaults it to "link" — every recipe that
    existed before images were supported is one."""
    repository = RecipeRepository(db_session)

    created = await repository.create(_build_recipe())

    assert created.source_type == "link"


async def test_given_a_recipe_from_images_when_created_then_it_persists_without_a_source_url(
    db_session: AsyncSession,
) -> None:
    """Given a recipe extracted from uploaded images, which has no source
    URL to point back to, when created, then it persists with a null
    source_url and a source_type recording where it came from."""
    repository = RecipeRepository(db_session)

    created = await repository.create(_build_recipe(source_url=None, source_type="image"))
    fetched = await repository.get(created.id)

    assert fetched is not None
    assert fetched.source_url is None
    assert fetched.source_type == "image"


async def test_given_a_persisted_recipe_when_fetched_by_id_then_it_is_returned(
    db_session: AsyncSession,
) -> None:
    """Given a recipe already persisted, when fetched by its id, then the
    same recipe (including JSONB fields) is returned."""
    repository = RecipeRepository(db_session)
    created = await repository.create(_build_recipe())

    fetched = await repository.get(created.id)

    assert fetched is not None
    assert fetched.title == "Bolo de cenoura"
    assert fetched.ingredients[0]["name"] == "cenoura"


async def test_given_no_recipe_with_the_given_id_when_fetched_then_returns_none(
    db_session: AsyncSession,
) -> None:
    """Given no recipe exists with a given id, when fetched, then None is
    returned instead of raising."""
    repository = RecipeRepository(db_session)

    fetched = await repository.get(uuid.uuid4())

    assert fetched is None


async def test_given_multiple_recipes_when_listed_then_returns_them_newest_first(
    db_session: AsyncSession,
) -> None:
    """Given several recipes were created, when listed, then they come back
    ordered from most recently created to oldest."""
    repository = RecipeRepository(db_session)
    first = await repository.create(_build_recipe(title="Primeiro"))
    second = await repository.create(_build_recipe(title="Segundo"))

    recipes = await repository.list()

    assert [recipe.id for recipe in recipes] == [second.id, first.id]


async def test_given_a_persisted_recipe_when_updated_then_the_changes_are_saved(
    db_session: AsyncSession,
) -> None:
    """Given a recipe already persisted, when updated with new field values,
    then those values are saved and returned."""
    repository = RecipeRepository(db_session)
    created = await repository.create(_build_recipe())

    updated = await repository.update(created.id, title="Bolo de cenoura com cobertura")

    assert updated is not None
    assert updated.title == "Bolo de cenoura com cobertura"


async def test_given_no_recipe_with_the_given_id_when_updated_then_returns_none(
    db_session: AsyncSession,
) -> None:
    """Given no recipe exists with a given id, when an update is attempted,
    then None is returned instead of raising."""
    repository = RecipeRepository(db_session)

    updated = await repository.update(uuid.uuid4(), title="Não existe")

    assert updated is None


async def test_given_a_persisted_recipe_when_deleted_then_it_no_longer_exists(
    db_session: AsyncSession,
) -> None:
    """Given a recipe already persisted, when deleted, then it can no longer
    be fetched and the deletion is reported as successful."""
    repository = RecipeRepository(db_session)
    created = await repository.create(_build_recipe())

    was_deleted = await repository.delete(created.id)
    fetched = await repository.get(created.id)

    assert was_deleted is True
    assert fetched is None


async def test_given_no_recipe_with_the_given_id_when_deleted_then_returns_false(
    db_session: AsyncSession,
) -> None:
    """Given no recipe exists with a given id, when a deletion is attempted,
    then False is returned instead of raising."""
    repository = RecipeRepository(db_session)

    was_deleted = await repository.delete(uuid.uuid4())

    assert was_deleted is False
