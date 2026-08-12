import { API_BASE_URL } from './config'
import type { Recipe } from './types'

export async function fetchRecipes(): Promise<Recipe[]> {
  const response = await fetch(`${API_BASE_URL}/api/recipes`)
  if (!response.ok) {
    throw new Error(`Falha ao buscar receitas (status ${response.status}).`)
  }
  return response.json() as Promise<Recipe[]>
}
