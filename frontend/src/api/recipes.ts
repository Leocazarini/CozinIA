import { API_BASE_URL } from './config'
import type { Recipe, UpdateRecipeInput } from './types'

/** An error whose message already comes translated for the end user. */
export class ApiError extends Error {}

export async function fetchRecipes(): Promise<Recipe[]> {
  const response = await fetch(`${API_BASE_URL}/api/recipes`)
  if (!response.ok) {
    throw new Error(`Falha ao buscar receitas (status ${response.status}).`)
  }
  return response.json() as Promise<Recipe[]>
}

export async function fetchRecipe(id: string): Promise<Recipe> {
  const response = await fetch(`${API_BASE_URL}/api/recipes/${id}`)
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response))
  }
  return response.json() as Promise<Recipe>
}

export async function createRecipe(url: string): Promise<Recipe> {
  const response = await fetch(`${API_BASE_URL}/api/recipes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response))
  }
  return response.json() as Promise<Recipe>
}

export async function updateRecipe(id: string, changes: UpdateRecipeInput): Promise<Recipe> {
  const response = await fetch(`${API_BASE_URL}/api/recipes/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response))
  }
  return response.json() as Promise<Recipe>
}

/**
 * The backend sends a Portuguese `detail` string for every known failure
 * (see backend/app/api/error_handlers.py) — pass it straight through. Falls
 * back to a generic message for anything else (e.g. FastAPI's own
 * validation errors, which shape `detail` as a list, not a string).
 */
async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && typeof (body as { detail?: unknown }).detail === 'string') {
      return (body as { detail: string }).detail
    }
  } catch {
    // Response wasn't JSON — fall through to the generic message.
  }
  return 'Não foi possível salvar a receita. Verifique o link e tente novamente.'
}
