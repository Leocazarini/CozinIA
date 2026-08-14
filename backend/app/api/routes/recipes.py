"""Recipe endpoints: create from a link, from photos, or from a video link
(all three via AI extraction), list, retrieve, update, delete."""

import asyncio
import uuid
from collections.abc import Sequence

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.rate_limit import CREATE_RECIPE_LIMIT, limiter
from app.core.security import get_current_user
from app.models.recipe import Recipe
from app.schemas.recipe import CreateRecipeRequest, RecipeResponse, UpdateRecipeRequest
from app.services.image_intake import (
    MAX_BYTES_PER_IMAGE,
    MAX_IMAGES,
    TooManyImagesError,
    prepare_images,
)
from app.services.recipe_service import RecipeService

# Every route here requires a valid login token: the recipe library is private
# to the app's accounts. /health and /api/auth/login are the only public doors.
router = APIRouter(
    prefix="/api/recipes",
    tags=["recipes"],
    dependencies=[Depends(get_current_user)],
)

_NOT_FOUND_DETAIL = "Receita não encontrada."

# Read one byte past the limit so an oversized upload is still detected when
# it is truncated here rather than read whole into memory.
_UPLOAD_READ_LIMIT = MAX_BYTES_PER_IMAGE + 1


def get_recipe_service(session: AsyncSession = Depends(get_db_session)) -> RecipeService:
    """FastAPI dependency building a RecipeService for the current request."""
    return RecipeService(session)


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(CREATE_RECIPE_LIMIT)
async def create_recipe(
    request: Request,
    payload: CreateRecipeRequest,
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Extract a recipe from the given URL and persist it.

    `request` is required by the rate limiter that caps how often this
    money-spending endpoint can be called from one caller.
    """
    return await service.create_from_url(str(payload.url))


@router.post("/image", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(CREATE_RECIPE_LIMIT)
async def create_recipe_from_images(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Extract a recipe from uploaded photos and persist it.

    The files are the pages of a single recipe, in the order sent. They are
    only a source of text: nothing is stored beyond the recipe itself.

    `files` defaults to an empty list rather than being required so that an
    empty submission is answered with our own Portuguese message (via
    NoImagesProvidedError) instead of FastAPI's generic validation error.

    `request` is required by the rate limiter on this money-spending endpoint.
    """
    # Reject an over-count *before* reading any file into memory: otherwise a
    # single request with hundreds of files would spool gigabytes to memory
    # and disk before prepare_images ever gets to complain about the number.
    if len(files) > MAX_IMAGES:
        raise TooManyImagesError(f"{len(files)} images sent, max is {MAX_IMAGES}")
    uploads = [(file.content_type, await file.read(_UPLOAD_READ_LIMIT)) for file in files]
    # Pillow decode + resize is CPU-bound and blocks the event loop; hand it to
    # a worker thread so one big upload can't freeze every other request.
    images = await asyncio.to_thread(prepare_images, uploads)
    return await service.create_from_images(images)


@router.post("/video", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(CREATE_RECIPE_LIMIT)
async def create_recipe_from_video(
    request: Request,
    payload: CreateRecipeRequest,
    service: RecipeService = Depends(get_recipe_service),
) -> Recipe:
    """Extract a recipe from the given video link and persist it.

    Takes the same payload as the link endpoint — a url is a url — but reads it
    as a video: its description and its narration, rather than the text of a
    page. Which door a link goes through is the user's choice, not something
    guessed from the host.

    `request` is required by the rate limiter on this money-spending endpoint.
    """
    return await service.create_from_video_url(str(payload.url))


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
