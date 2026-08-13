/**
 * Where the API lives: the same origin that served the app.
 *
 * Nothing about the backend's address is written down here, and that is the
 * point. In production a reverse proxy publishes the built app at `/` and the
 * backend at `/api` on one origin; in development the Vite server proxies the
 * same two prefixes (see `vite.config.ts`). Either way the browser only ever
 * talks to the host it loaded the page from.
 *
 * Being same-origin is what makes the app installable at all: a service worker
 * needs a secure context, and an https page calling a plain-http backend on
 * another port would be blocked as mixed content. It also means the LAN and
 * the VPS run the identical build — only the certificate and the server name
 * differ — and that no request ever needs CORS.
 *
 * VITE_API_URL stays as an escape hatch for pointing the frontend at a backend
 * that is *not* behind the same proxy. Deliberately `||` and not `??`:
 * docker-compose passes the variable through as an *empty string* when it is
 * unset on the host, and `??` would take that empty string as a configured
 * value — which happens to be the default anyway, but for the wrong reason.
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || ''
