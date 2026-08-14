import { API_BASE_URL } from './config'
import { clearToken, getToken } from './authToken'

/** An error whose message already comes translated for the end user. */
export class ApiError extends Error {}

// Called when any request comes back 401 (an expired or missing token). The
// AuthProvider registers a handler that drops the session and sends the user
// back to the login screen.
let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

/**
 * fetch for the app's own API: prefixes the base URL, attaches the bearer
 * token when there is one, and reacts to a 401 by clearing the token and
 * notifying the app so it can show the login screen.
 *
 * When there is no token, the request is passed through untouched (no headers
 * added) so callers like the multipart upload keep letting the browser set
 * their own Content-Type.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken()

  let request = init
  if (token) {
    const headers = new Headers(init.headers)
    headers.set('Authorization', `Bearer ${token}`)
    request = { ...init, headers }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, request)

  if (response.status === 401) {
    clearToken()
    onUnauthorized?.()
  }

  return response
}

/**
 * The backend sends a Portuguese `detail` string for every known failure
 * (see backend/app/api/error_handlers.py) — pass it straight through. Falls
 * back to a generic message for anything else (e.g. FastAPI's own validation
 * errors, which shape `detail` as a list, not a string).
 */
export async function extractErrorMessage(
  response: Response,
  fallback = 'Não foi possível salvar a receita. Tente novamente.',
): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (
      body &&
      typeof body === 'object' &&
      typeof (body as { detail?: unknown }).detail === 'string'
    ) {
      return (body as { detail: string }).detail
    }
  } catch {
    // Response wasn't JSON — fall through to the generic message.
  }
  return fallback
}
