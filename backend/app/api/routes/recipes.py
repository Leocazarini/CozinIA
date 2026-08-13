"""Recipe endpoints: create from a link, from photos, or from a video link
(all three via AI extraction), list, retrieve, update, delete."""

import uuid
from collections.abc import Sequence

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.models.recipe import Recipe
from app.schemas.recipe import CreateRecipeRequest, RecipeResponse, UpdateRecipeRequest
from app.services.image_intake import MAX_BYTES_PER_IMAGE, prepare_images
from app.services.recipe_service import RecipeService

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

_NOT_FOUND_DETAIL = "Receita não encontrada."

# Read one byte past the limit so an oversized upload is still detected when
# it is truncated here rather than read whole into memory.
_UPLOAD_READ_LIMIT = MAX_BYTES_PER_IMAGE + 1


def get_recipe_service(session: AsyncSession = Depends(get_db_session)) -> RecipeService:
    """FastAPI dependency building a RecipeService for the current request."""
    return RecipeService(session)


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    request: CreateRecipeRequest,
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Extract a recipe from the given URL and persist it."""
    return await service.create_from_url(str(request.url))


@router.post("/image", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe_from_images(
    files: list[UploadFile] = File(default=[]),
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Extract a recipe from uploaded photos and persist it.

    The files are the pages of a single recipe, in the order sent. They are
    only a source of text: nothing is stored beyond the recipe itself.

    `files` defaults to an empty list rather than being required so that an
    empty submission is answered with our own Portuguese message (via
    NoImagesProvidedError) instead of FastAPI's generic validation error.
    """
    uploads = [(file.content_type, await file.read(_UPLOAD_READ_LIMIT)) for file in files]
    images = prepare_images(uploads)
    return await service.create_from_images(images)


@router.post("/video", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe_from_video(
    request: CreateRecipeRequest,
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Extract a recipe from the given video link and persist it.

    Takes the same payload as the link endpoint — a url is a url — but reads it
    as a video: its description and its narration, rather than the text of a
    page. Which door a link goes through is the user's choice, not something
    guessed from the host.
    """
    return await service.create_from_video_url(str(request.url))


@router.get("", response_model=list[RecipeResponse])
async def list_recipes(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: RecipeService = Depends(get_recipe_service),
) -> Sequence[Recipe]:
    """List saved recipes, most recently created first."""
    return await service.list(limit=limit, offset=offset)


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: uuid.UUID,
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Fetch a single recipe by id."""
    recipe = await service.get(recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL)
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(
    recipe_id: uuid.UUID,
    request: UpdateRecipeRequest,
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Apply a manual, partial edit to a recipe (e.g. to fix an AI mistake)."""
    fields = request.model_dump(exclude_unset=True)
    recipe = await service.update(recipe_id, **fields)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL)
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: uuid.UUID,
    service: RecipeService = Depends(get_recipe_service),
) -> None:
    """Delete a recipe."""
    was_deleted = await service.delete(recipe_id)
    if not was_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL)
