/**
 * Where the login token lives on the device.
 *
 * localStorage (not sessionStorage) so an installed PWA stays signed in across
 * launches — a kitchen app that asked for the password every time it opened
 * would not get used. The token is a bearer credential: the app has no XSS
 * sinks (every value is rendered as escaped React text) and the served pages
 * carry a strict Content-Security-Policy, which is what keeps a stored token
 * out of a script's reach.
 */
const TOKEN_KEY = 'cozinia-token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    // localStorage can throw in private-mode / storage-disabled contexts.
    return null
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Nothing to do: without storage the session simply won't persist.
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Ignore — see getToken.
  }
}
