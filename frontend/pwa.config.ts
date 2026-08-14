import type { VitePWAOptions } from 'vite-plugin-pwa'

/**
 * Everything that turns the built app into an installable one: the manifest
 * Android and iOS read when it goes onto the home screen, and the Workbox
 * rules the generated service worker is built from.
 *
 * Kept out of `vite.config.ts` so the contract can be asserted directly by
 * `tests/pwa/config.test.ts` — none of this is reachable from jsdom, and
 * silently losing a rule here shows up as "the app stopped working in the
 * kitchen", not as a failing build.
 */
export const pwaOptions: Partial<VitePWAOptions> = {
  registerType: 'autoUpdate',
  includeAssets: ['icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png'],

  manifest: {
    // User-facing metadata — kept in Portuguese on purpose.
    name: 'CozinIA',
    short_name: 'CozinIA',
    description: 'Salve receitas a partir de um link e organize tudo em um só lugar.',
    lang: 'pt-BR',
    // The install identity. Derived from `start_url` when absent, which
    // would make any later change to that URL install a second app instead
    // of updating this one.
    id: '/',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    orientation: 'portrait',
    theme_color: '#f2efe4',
    background_color: '#f2efe4',
    icons: [
      { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
      // Same artwork, inset into the safe zone Android needs to crop the
      // icon into whatever shape the launcher uses.
      {
        src: 'icons/icon-maskable-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  },

  workbox: {
    // The default glob covers the code and the images but not woff2, and the
    // fonts are self-hosted (@fontsource) — part of the app, not a
    // third-party request.
    globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest,woff2}'],
    cleanupOutdatedCaches: true,

    // Client-side routes (/adicionar, /recipes/:id) have no file behind
    // them, so any navigation is served the cached shell instead. The
    // denylist matters now that the API shares this origin: without it the
    // service worker would answer fetch('/api/recipes') with index.html,
    // turning "offline" into a JSON parse error.
    navigateFallback: '/index.html',
    navigateFallbackDenylist: [/^\/api\//, /^\/health$/],

    runtimeCaching: [
      {
        // Network first: online, the kitchen sees the recipe as it stands
        // now; the cache only answers when the network doesn't, which is
        // what lets a recipe be read with no signal.
        urlPattern: /\/api\/recipes(?:\/|$|\?)/,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'cozinia-recipes',
          networkTimeoutSeconds: 4,
          expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 * 30 },
          cacheableResponse: { statuses: [200] },
        },
      },
      {
        // Recipe photos live on whatever site the recipe came from. Matched
        // by destination rather than by extension because plenty of those
        // URLs end in a query string, or in nothing at all.
        urlPattern: ({ request, sameOrigin }) => !sameOrigin && request.destination === 'image',
        // StaleWhileRevalidate, not CacheFirst: a CacheFirst entry pins a
        // third-party image for its whole lifetime, so a changed or
        // compromised URL would keep serving the old bytes; this refreshes it
        // in the background instead. maxEntries kept modest because opaque
        // cross-origin responses (status 0) are padded to several MB each in
        // the browser's quota accounting, so a large cap could evict the
        // precached app shell and break offline use.
        handler: 'StaleWhileRevalidate',
        options: {
          cacheName: 'cozinia-recipe-images',
          expiration: { maxEntries: 25, maxAgeSeconds: 60 * 60 * 24 * 7 },
          // Cross-origin images fetched no-cors come back opaque, with
          // status 0. Accepting only 200 would cache none of them.
          cacheableResponse: { statuses: [0, 200] },
        },
      },
    ],
  },
}
