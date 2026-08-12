// Port the backend is published on by docker-compose.
const BACKEND_PORT = 8000

/**
 * Where the API lives, when nothing was configured explicitly.
 *
 * Derived from the address that served the page rather than hardcoded to
 * localhost: the browser reaches the backend on the same host it just
 * loaded the app from, only on a different port. Opening the app from a
 * phone at http://192.168.x.x:5173 therefore calls
 * http://192.168.x.x:8000 — where hardcoding "localhost" would make the
 * phone call *itself*, which is exactly the machine with no backend on it.
 *
 * This also survives the LAN IP changing, which a value pinned in .env
 * does not.
 */
function sameHostApiBaseUrl(): string {
  const { protocol, hostname } = window.location
  return `${protocol}//${hostname}:${BACKEND_PORT}`
}

// VITE_API_URL stays as an escape hatch for pointing the frontend at a
// backend that is *not* on the same host (see docker-compose.yml).
// Deliberately `||` and not `??`: docker-compose passes the variable
// through as an *empty string* when it is unset on the host, and an empty
// base URL would silently turn every API call into a relative one.
export const API_BASE_URL = import.meta.env.VITE_API_URL || sameHostApiBaseUrl()
