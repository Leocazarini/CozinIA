import { ApiError, apiFetch, extractErrorMessage } from './client'
import type { Recipe, UpdateRecipeInput } from './types'

export { ApiError }

export async function fetchRecipes(): Promise<Recipe[]> {
  const response = await apiFetch('/api/recipes')
  if (!response.ok) {
    throw new Error(`Falha ao buscar receitas (status ${response.status}).`)
  }
  return response.json() as Promise<Recipe[]>
}

export async function fetchRecipe(id: string): Promise<Recipe> {
  const response = await apiFetch(`/api/recipes/${encodeURIComponent(id)}`)
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response))
  }
  return response.json() as Promise<Recipe>
}

export async function createRecipe(url: string): Promise<Recipe> {
  const response = await apiFetch('/api/recipes', {
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

  const response = await apiFetch('/api/recipes/image', {
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
  const response = await apiFetch('/api/recipes/video', {
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
  const response = await apiFetch(`/api/recipes/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response))
  }
  return response.json() as Promise<Recipe>
}
