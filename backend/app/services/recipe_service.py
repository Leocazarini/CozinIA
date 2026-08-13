"""Orchestrates the recipe extraction flow: read the source -> extract ->
persist.

Two kinds of source converge here — a link, which is scraped, and uploaded
photos, which are transcribed. Both produce text, so everything from the AI
extraction onwards is shared, and a persisted recipe is the same kind of
thing whichever way it arrived.
"""

import uuid
from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.recipe import Recipe
from app.repositories.recipe_repository import RecipeRepository
from app.schemas.recipe import RecipeExtraction
from app.services.ai_extractor import extract_recipe
from app.services.image_transcriber import transcribe_images
from app.services.scraper import fetch_and_extract_text

ScrapeFn = Callable[[str], Awaitable[str]]
TranscribeFn = Callable[[Sequence[bytes]], Awaitable[str]]
ExtractFn = Callable[[str], Awaitable[RecipeExtraction]]

_AI_PROVIDER_NAME = "openrouter"
_LINK_SOURCE = "link"
_IMAGE_SOURCE = "image"


class RecipeService:
    """Coordinates source reading, AI extraction, and persistence for
    recipes."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        scrape: ScrapeFn = fetch_and_extract_text,
        transcribe: TranscribeFn = transcribe_images,
        extract: ExtractFn = extract_recipe,
    ) -> None:
        self._repository = RecipeRepository(session)
        self._scrape = scrape
        self._transcribe = transcribe
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
        return await self._persist(
            extraction, source_url=source_url, source_type=_LINK_SOURCE, raw_text=text
        )

    async def create_from_images(self, images: Sequence[bytes]) -> Recipe:
        """Transcribe `images` — the pages of a single recipe, in order —
        extract the recipe from that text via AI, and persist the result.

        The images themselves are not stored, so the transcription kept in
        `raw_extracted_text` is the only record of what was read.

        Lets UnreadableImageError, AIRequestError, MalformedAIResponseError
        and NotARecipeError propagate unchanged — the API layer is
        responsible for translating them into user-facing responses.
        """
        text = await self._transcribe(images)
        extraction = await self._extract(text)
        return await self._persist(
            extraction, source_url=None, source_type=_IMAGE_SOURCE, raw_text=text
        )

    async def _persist(
        self,
        extraction: RecipeExtraction,
        *,
        source_url: str | None,
        source_type: str,
        raw_text: str,
    ) -> Recipe:
        """Build and store a Recipe from an extraction plus its provenance —
        the part both creation flows share."""
        settings = get_settings()

        recipe = Recipe(
            source_url=source_url,
            source_type=source_type,
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
            raw_extracted_text=raw_text,
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
