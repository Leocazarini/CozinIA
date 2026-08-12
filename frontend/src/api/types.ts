// Mirrors the backend's Pydantic schemas (see backend/app/schemas/recipe.py).
// Field names are kept snake_case, matching the JSON wire format exactly —
// no case-mapping layer, to keep the API client a direct, obvious reflection
// of what the backend actually sends.

export interface Ingredient {
  name: string
  quantity: string | null
  unit: string | null
  notes: string | null
}

export interface Step {
  order: number
  text: string
}

export interface Recipe {
  id: string
  source_url: string
  title: string
  description: string | null
  image_url: string | null
  prep_time_minutes: number | null
  cook_time_minutes: number | null
  total_time_minutes: number | null
  servings: number | null
  ingredients: Ingredient[]
  steps: Step[]
  tags: string[] | null
  ai_provider: string | null
  ai_model: string | null
  created_at: string
  updated_at: string
}

/** Partial edit payload for PATCH /api/recipes/{id} — mirrors UpdateRecipeRequest. */
export interface UpdateRecipeInput {
  title?: string
  description?: string | null
  image_url?: string | null
  prep_time_minutes?: number | null
  cook_time_minutes?: number | null
  total_time_minutes?: number | null
  servings?: number | null
  ingredients?: Ingredient[]
  steps?: Step[]
  tags?: string[] | null
}
