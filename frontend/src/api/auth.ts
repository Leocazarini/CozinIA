import { API_BASE_URL } from './config'
import { ApiError, extractErrorMessage } from './client'
import { clearToken, setToken } from './authToken'

interface TokenResponse {
  access_token: string
  token_type: string
}

/**
 * Exchange a username and password for a token and store it.
 *
 * Uses plain fetch rather than apiFetch: a 401 here means "wrong credentials",
 * a normal outcome to surface on the form — not the "session expired" signal
 * apiFetch turns a 401 into everywhere else.
 */
export async function login(username: string, password: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    throw new ApiError(
      await extractErrorMessage(response, 'Não foi possível entrar. Tente novamente.'),
    )
  }

  const body = (await response.json()) as TokenResponse
  setToken(body.access_token)
}

export function logout(): void {
  clearToken()
}
