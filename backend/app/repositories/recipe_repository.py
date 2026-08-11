"""Data access layer for recipes."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Recipe


class RecipeRepository:
    """Encapsulates all database access for the Recipe aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, recipe: Recipe) -> Recipe:
        """Persist a new recipe and return it with generated fields populated."""
        self._session.add(recipe)
        await self._session.commit()
        await self._session.refresh(recipe)
        return recipe

    async def get(self, recipe_id: uuid.UUID) -> Recipe | None:
        """Return the recipe with the given id, or None if it does not exist."""
        return await self._session.get(Recipe, recipe_id)

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[Recipe]:
        """Return recipes ordered from most recently created to oldest."""
        statement = (
            select(Recipe).order_by(Recipe.created_at.desc()).limit(limit).offset(offset)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def update(self, recipe_id: uuid.UUID, **fields: object) -> Recipe | None:
        """Apply a partial update to an existing recipe. Returns None if it does not exist."""
        recipe = await self.get(recipe_id)
        if recipe is None:
            return None
        for field_name, value in fields.items():
            setattr(recipe, field_name, value)
        await self._session.commit()
        await self._session.refresh(recipe)
        return recipe

    async def delete(self, recipe_id: uuid.UUID) -> bool:
        """Delete the recipe with the given id. Returns True if it existed."""
        recipe = await self.get(recipe_id)
        if recipe is None:
            return False
        await self._session.delete(recipe)
        await self._session.commit()
        return True
