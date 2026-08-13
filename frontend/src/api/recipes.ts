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

/**
 * Sends photos of one recipe — its pages, in order — as multipart form data.
 * `Content-Type` is deliberately not set: the browser has to generate it
 * itself so it can include the multipart boundary.
 */
export async function createRecipeFromImages(files: File[]): Promise<Recipe> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }

  const response = await fetch(`${API_BASE_URL}/api/recipes/image`, {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response))
  }
  return response.json() as Promise<Recipe>
}

/**
 * Sends the link of a video to be read as a video — its narration and its
 * description — rather than scraped as a page. Which door a link goes through
 * is the user's choice, not something guessed from the host.
 */
export async function createRecipeFromVideo(url: string): Promise<Recipe> {
  const response = await fetch(`${API_BASE_URL}/api/recipes/video`, {
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
  return 'Não foi possível salvar a receita. Tente novamente.'
}
