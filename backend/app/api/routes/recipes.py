"""Recipe endpoints: create (via AI extraction), list, retrieve, update, delete."""

import uuid
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.models.recipe import Recipe
from app.schemas.recipe import CreateRecipeRequest, RecipeResponse, UpdateRecipeRequest
from app.services.recipe_service import RecipeService

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

_NOT_FOUND_DETAIL = "Receita não encontrada."


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
