"""Orchestrates the recipe extraction flow: scrape -> extract -> persist."""

import uuid
from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.recipe import Recipe
from app.repositories.recipe_repository import RecipeRepository
from app.schemas.recipe import RecipeExtraction
from app.services.ai_extractor import extract_recipe
from app.services.scraper import fetch_and_extract_text

ScrapeFn = Callable[[str], Awaitable[str]]
ExtractFn = Callable[[str], Awaitable[RecipeExtraction]]

_AI_PROVIDER_NAME = "openrouter"


class RecipeService:
    """Coordinates scraping, AI extraction, and persistence for recipes."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        scrape: ScrapeFn = fetch_and_extract_text,
        extract: ExtractFn = extract_recipe,
    ) -> None:
        self._repository = RecipeRepository(session)
        self._scrape = scrape
        self._extract = extract

    async def create_from_url(self, source_url: str) -> Recipe:
        """Fetch the page at `source_url`, extract its recipe via AI, and
        persist the result.

        Lets UnreachableUrlError, NoExtractableContentError, AIRequestError,
        MalformedAIResponseError and NotARecipeError propagate unchanged —
        the API layer is responsible for translating them into user-facing
        responses.
        """
        text = await self._scrape(source_url)
        extraction = await self._extract(text)
        settings = get_settings()

        recipe = Recipe(
            source_url=source_url,
            title=extraction.title,
            description=extraction.description,
            image_url=extraction.image_url,
            prep_time_minutes=extraction.prep_time_minutes,
            cook_time_minutes=extraction.cook_time_minutes,
            total_time_minutes=extraction.total_time_minutes,
            servings=extraction.servings,
            ingredients=[ingredient.model_dump() for ingredient in extraction.ingredients],
            steps=[step.model_dump() for step in extraction.steps],
            tags=extraction.tags,
            raw_extracted_text=text,
            ai_provider=_AI_PROVIDER_NAME,
            ai_model=settings.ai_model,
        )
        return await self._repository.create(recipe)

    async def get(self, recipe_id: uuid.UUID) -> Recipe | None:
        """Fetch a single recipe by id."""
        return await self._repository.get(recipe_id)

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[Recipe]:
        """List saved recipes, most recently created first."""
        return await self._repository.list(limit=limit, offset=offset)

    async def update(self, recipe_id: uuid.UUID, **fields: object) -> Recipe | None:
        """Apply a partial manual edit to a recipe (e.g. to fix an AI mistake)."""
        return await self._repository.update(recipe_id, **fields)

    async def delete(self, recipe_id: uuid.UUID) -> bool:
        """Delete a recipe."""
        return await self._repository.delete(recipe_id)
