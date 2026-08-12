import type { Recipe } from '../../src/api/types'

/** Builds a valid Recipe for tests, with sensible defaults overridable per-case. */
export function buildRecipe(overrides: Partial<Recipe> = {}): Recipe {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    source_url: 'https://example.com/receita',
    title: 'Receita de teste',
    description: null,
    image_url: null,
    prep_time_minutes: null,
    cook_time_minutes: null,
    total_time_minutes: null,
    servings: null,
    ingredients: [],
    steps: [],
    tags: null,
    ai_provider: null,
    ai_model: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}
