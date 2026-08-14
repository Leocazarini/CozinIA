import { describe, expect, it } from 'vitest'
import { pwaOptions } from '../../pwa.config'

/**
 * The service worker and the manifest can only be exercised for real in a
 * browser, against a built app served over https — there is no service worker
 * in jsdom. What *can* be pinned down here is the configuration they are
 * generated from, and every assertion below stands for something the user
 * would notice on their phone if it silently changed.
 */

const manifest = pwaOptions.manifest!
const workbox = pwaOptions.workbox!

function ruleFor(cacheName: string) {
  const rule = workbox.runtimeCaching?.find((entry) => entry.options?.cacheName === cacheName)
  if (!rule) {
    throw new Error(`No runtime caching rule named "${cacheName}".`)
  }
  return rule
}

/** The app's own origin, as far as these tests are concerned. */
const APP_ORIGIN = 'https://cozinia.example'

/**
 * Asks a routing rule the same question the service worker asks it at
 * runtime: would you handle this request?
 */
function matches(pattern: unknown, url: string, destination = 'document'): boolean {
  if (pattern instanceof RegExp) {
    return pattern.test(url)
  }
  if (typeof pattern === 'function') {
    const parsed = new URL(url)
    return Boolean(
      pattern({
        url: parsed,
        request: { destination } as Request,
        sameOrigin: parsed.origin === APP_ORIGIN,
      }),
    )
  }
  throw new Error('Unsupported urlPattern type.')
}

describe('installed app manifest', () => {
  it('given the app is installed, when it is opened from the home screen, then it runs standalone in Portuguese', () => {
    // `display: standalone` is the difference between an app and a browser
    // tab: no address bar, no browser chrome, its own entry in the task
    // switcher.
    expect(manifest.display).toBe('standalone')
    expect(manifest.lang).toBe('pt-BR')
    expect(manifest.name).toBe('CozinIA')
  })

  it('given the app is installed, when the browser decides what belongs to it, then scope and identity cover the whole app', () => {
    // Without an explicit `id`, the install identity is derived from
    // `start_url` — moving that later would install a *second* app instead
    // of updating this one. `scope` is what keeps in-app navigations from
    // being handed back to the browser.
    expect(manifest.id).toBe('/')
    expect(manifest.scope).toBe('/')
    expect(manifest.start_url).toBe('/')
  })

  it('given Android draws the launcher icon in its own shape, when it masks it, then a maskable icon is offered', () => {
    // Android crops any non-maskable icon into its shape without knowing
    // where the artwork ends — the maskable variant carries the safe zone.
    const maskable = manifest.icons?.find((icon) => icon.purpose === 'maskable')

    expect(maskable).toMatchObject({ sizes: '512x512', type: 'image/png' })
  })
})

describe('offline reading', () => {
  it('given a recipe was opened before, when it is opened again with no connection, then the cached response answers', () => {
    const rule = ruleFor('cozinia-recipes')

    expect(matches(rule.urlPattern, `${APP_ORIGIN}/api/recipes`)).toBe(true)
    expect(matches(rule.urlPattern, `${APP_ORIGIN}/api/recipes/abc-123`)).toBe(true)
    // Network first, not cache first: online, the kitchen still gets the
    // recipe as it stands now, with the cache only as a fallback.
    expect(rule.handler).toBe('NetworkFirst')
    expect(rule.options?.networkTimeoutSeconds).toBeGreaterThan(0)
  })

  it('given a cached recipe has a photo, when it is read offline, then the photo comes from the cache too', () => {
    const rule = ruleFor('cozinia-recipe-images')

    expect(matches(rule.urlPattern, 'https://algum-site.com/foto.jpg?w=800', 'image')).toBe(true)
    expect(matches(rule.urlPattern, 'https://algum-site.com/receita', 'document')).toBe(false)
    // Opaque cross-origin responses arrive with status 0; refusing those
    // would mean caching no external photo at all.
    expect(rule.options?.cacheableResponse?.statuses).toContain(0)
  })

  it('given the app is offline, when it falls back to the cached shell, then API calls are not answered with HTML', () => {
    // The navigation fallback exists for client-side routes like
    // /recipes/:id. Now that the API shares the origin, an unguarded
    // fallback would hand index.html to fetch() and turn a network error
    // into a JSON parse error.
    expect(workbox.navigateFallback).toBe('/index.html')

    const denied = (path: string) =>
      (workbox.navigateFallbackDenylist ?? []).some((pattern) => pattern.test(path))

    expect(denied('/api/recipes')).toBe(true)
    expect(denied('/health')).toBe(true)
    expect(denied('/recipes/abc-123')).toBe(false)
  })

  it('given the app is opened with no connection, when the shell renders, then its own fonts are already cached', () => {
    // The fonts are self-hosted (@fontsource), so they are part of the app,
    // not a third-party request — but Workbox's default glob does not
    // include woff2, and without them the offline app falls back to a
    // system serif and stops looking like itself.
    expect(workbox.globPatterns?.join(' ')).toContain('woff2')
  })
})
