import { HttpResponse, http } from 'msw'
import { API_BASE_URL } from '../../src/api/config'
import type { Recipe } from '../../src/api/types'

// Default happy-path handlers — individual tests override these via
// `server.use(...)` for the scenario they're exercising (empty, error, etc).
export const handlers = [
  http.get(`${API_BASE_URL}/api/recipes`, () => HttpResponse.json<Recipe[]>([])),
]
