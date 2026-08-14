import { afterEach, describe, expect, it, vi } from 'vitest'
import { createRecipeFromImages, fetchRecipes } from '../../src/api/recipes'
import { buildRecipe } from '../factories/recipe'

/**
 * `fetch` is stubbed rather than intercepted with MSW so the request body can
 * be read as the browser would see it. jsdom's FormData loses filenames and
 * file contents once a request crosses into the HTTP layer, which is exactly
 * what this file needs to inspect.
 */
function stubFetch() {
  const stub = vi.fn(async () => new Response(JSON.stringify(buildRecipe()), { status: 201 }))
  vi.stubGlobal('fetch', stub)
  return stub
}

function sentForm(stub: ReturnType<typeof stubFetch>): FormData {
  return stub.mock.calls[0][1].body as FormData
}

afterEach(() => vi.unstubAllGlobals())

describe('where the API lives', () => {
  it('given no API URL is configured, when a recipe list is requested, then it is asked of the same origin that served the app', async () => {
    // The whole mobile app rests on this: the page, the service worker and
    // the API share one origin, so an https page never calls plain http
    // (blocked as mixed content) and the same build works unchanged behind
    // the reverse proxy on the LAN and on the VPS.
    const stub = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }))
    vi.stubGlobal('fetch', stub)

    await fetchRecipes()

    const requested = new URL(stub.mock.calls[0][0] as string, window.location.href)
    expect(requested.origin).toBe(window.location.origin)
    expect(requested.pathname).toBe('/api/recipes')
  })
})

describe('createRecipeFromImages', () => {
  it('given the pages of one recipe, when sending them, then they are attached in the order given', async () => {
    // Order is the contract: the backend tells the vision model to read the
    // images in sequence, so page 2 arriving first would put the method
    // before the ingredients.
    const stub = stubFetch()
    const pages = [
      new File(['p1'], 'pagina1.jpg', { type: 'image/jpeg' }),
      new File(['p2'], 'pagina2.jpg', { type: 'image/jpeg' }),
    ]

    await createRecipeFromImages(pages)

    const attached = sentForm(stub).getAll('files') as File[]
    expect(attached.map((file) => file.name)).toEqual(['pagina1.jpg', 'pagina2.jpg'])
  })

  it('given photos to send, when building the request, then it sets no Content-Type of its own', async () => {
    // The browser must generate it, because only it knows the multipart
    // boundary — setting it by hand produces a body the server can't parse.
    const stub = stubFetch()

    await createRecipeFromImages([new File(['p1'], 'pagina1.jpg', { type: 'image/jpeg' })])

    expect(stub.mock.calls[0][1].headers).toBeUndefined()
  })

  it('given the backend rejects the photos, when sending them, then its Portuguese message is surfaced unchanged', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: 'Envie pelo menos uma imagem da receita.' }), {
            status: 422,
          }),
      ),
    )

    await expect(createRecipeFromImages([])).rejects.toThrow(
      'Envie pelo menos uma imagem da receita.',
    )
  })
})
