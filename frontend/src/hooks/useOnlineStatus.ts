import { useSyncExternalStore } from 'react'

function subscribe(onChange: () => void): () => void {
  window.addEventListener('online', onChange)
  window.addEventListener('offline', onChange)
  return () => {
    window.removeEventListener('online', onChange)
    window.removeEventListener('offline', onChange)
  }
}

/**
 * Whether the browser currently believes it has a network.
 *
 * Matters because the installed app keeps working with no signal — the
 * service worker answers with the recipes already read — so "nothing is
 * loading" stops being an obvious explanation. Anything that genuinely needs
 * the server (extracting a new recipe) has to say so itself.
 *
 * `navigator.onLine` only knows whether there is *a* network, not whether the
 * server is reachable through it. That is enough for the one thing it is used
 * for: turning a bare network error into a sentence the user can act on.
 */
export function useOnlineStatus(): boolean {
  return useSyncExternalStore(subscribe, () => navigator.onLine)
}
