import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API_BASE_URL } from '../../src/api/config'
import { AddRecipe } from '../../src/pages/AddRecipe'
import { buildRecipe } from '../factories/recipe'
import { server } from '../mocks/server'

function renderAddRecipe() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AddRecipe />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/**
 * The three doors are tabs now, so every flow starts by opening its own —
 * only the selected door's form is mounted at any time.
 */
async function openTab(name: string) {
  const user = userEvent.setup()
  await user.click(screen.getByRole('tab', { name }))
}

async function submitUrl(url: string) {
  const user = userEvent.setup()
  await openTab('Link')
  await user.type(screen.getByLabelText('Link da receita'), url)
  await user.click(screen.getByRole('button', { name: 'Adicionar receita' }))
}

function photoNamed(name: string) {
  // The bytes carry the name so the request can be checked by content:
  // jsdom's FormData loses filenames on the way through fetch (every part
  // arrives as "blob"), but the bytes survive intact.
  return new File([`bytes-de-${name}`], name, { type: 'image/jpeg' })
}

async function choosePhotos(...names: string[]) {
  const user = userEvent.setup()
  await openTab('Imagem')
  await user.upload(screen.getByLabelText('Fotos da receita'), names.map(photoNamed))
}

async function submitPhotos(...names: string[]) {
  const user = userEvent.setup()
  await choosePhotos(...names)
  await user.click(screen.getByRole('button', { name: 'Extrair das fotos' }))
}

async function submitVideo(url: string) {
  const user = userEvent.setup()
  await openTab('Vídeo')
  await user.type(screen.getByLabelText('Link do vídeo'), url)
  await user.click(screen.getByRole('button', { name: 'Extrair do vídeo' }))
}

describe('AddRecipe', () => {
  it('given the page has just opened, then the three doors are offered as tabs, image first and selected', () => {
    renderAddRecipe()

    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
      'Imagem',
      'Vídeo',
      'Link',
    ])
    expect(screen.getByRole('tab', { name: 'Imagem' })).toHaveAttribute('aria-selected', 'true')
  })

  it('given a door is open, then the other two doors are closed', async () => {
    // One form on screen at a time is the point of the change: three stacked
    // forms made the page read as three tasks instead of one with a choice.
    renderAddRecipe()
    expect(screen.getByLabelText('Fotos da receita')).toBeInTheDocument()

    await openTab('Link')

    expect(screen.getByLabelText('Link da receita')).toBeInTheDocument()
    expect(screen.queryByLabelText('Fotos da receita')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Link do vídeo')).not.toBeInTheDocument()
  })

  it('given something already typed in a door, when the user looks at another and comes back, then what was typed is still there', async () => {
    const user = userEvent.setup()
    renderAddRecipe()

    await openTab('Link')
    await user.type(screen.getByLabelText('Link da receita'), 'https://example.com/bolo')
    await openTab('Vídeo')
    await openTab('Link')

    expect(screen.getByLabelText('Link da receita')).toHaveValue('https://example.com/bolo')
  })

  it('given a focused tab, when the user presses the right arrow, then the next door opens', async () => {
    const user = userEvent.setup()
    renderAddRecipe()

    await user.click(screen.getByRole('tab', { name: 'Imagem' }))
    await user.keyboard('{ArrowRight}')

    expect(screen.getByRole('tab', { name: 'Vídeo' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByLabelText('Link do vídeo')).toBeInTheDocument()
  })

  it('given a valid recipe link, when the extraction succeeds, then it shows a success message with the recipe title', async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/recipes`, () =>
        HttpResponse.json(buildRecipe({ title: 'Bolo de cenoura' }), { status: 201 }),
      ),
    )

    renderAddRecipe()
    await submitUrl('https://example.com/bolo-de-cenoura')

    expect(await screen.findByText(/Bolo de cenoura/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver receitas' })).toBeInTheDocument()
  })

  it('given the source page is unreachable, when the user submits, then it shows the API error message in Portuguese', async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/recipes`, () =>
        HttpResponse.json(
          { detail: 'Não foi possível acessar o link informado.' },
          { status: 422 },
        ),
      ),
    )

    renderAddRecipe()
    await submitUrl('https://example.com/pagina-fora-do-ar')

    expect(
      await screen.findByText('Não foi possível acessar o link informado.'),
    ).toBeInTheDocument()
  })

  it('given photos of a recipe, when the extraction succeeds, then it shows the same success message as a link would', async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/recipes/image`, () =>
        HttpResponse.json(
          buildRecipe({ title: 'Bolo da vovó', source_url: null, source_type: 'image' }),
          { status: 201 },
        ),
      ),
    )

    renderAddRecipe()
    await submitPhotos('pagina1.jpg', 'pagina2.jpg')

    expect(await screen.findByText(/Bolo da vovó/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver receitas' })).toBeInTheDocument()
  })

  it('given a recipe spanning two photos, when the user submits, then both go up in a single request', async () => {
    // Both pages in one call is the whole point: the vision model has to see
    // them together to read one recipe out of two pages. Their *order* is
    // specified where it can be observed — jsdom's FormData drops filenames
    // and contents on the way through fetch (see tests/api/recipes.test.ts).
    let requestCount = 0
    let partCount = 0
    server.use(
      http.post(`${API_BASE_URL}/api/recipes/image`, async ({ request }) => {
        requestCount += 1
        partCount = (await request.formData()).getAll('files').length
        return HttpResponse.json(buildRecipe(), { status: 201 })
      }),
    )

    renderAddRecipe()
    await submitPhotos('pagina1.jpg', 'pagina2.jpg')

    await screen.findByRole('link', { name: 'Ver receitas' })
    expect(requestCount).toBe(1)
    expect(partCount).toBe(2)
  })

  it('given no photo has been chosen, then the photo submit button is disabled', () => {
    renderAddRecipe()

    expect(screen.getByRole('button', { name: 'Extrair das fotos' })).toBeDisabled()
  })

  it('given several chosen photos, when the user removes one, then it is no longer listed', async () => {
    const user = userEvent.setup()
    renderAddRecipe()

    await choosePhotos('pagina1.jpg', 'pagina2.jpg')
    expect(screen.getByRole('button', { name: 'Remover foto 2' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Remover foto 1' }))

    expect(screen.queryByRole('button', { name: 'Remover foto 2' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remover foto 1' })).toBeInTheDocument()
  })

  it('given the photos are not a recipe, when the user submits, then it shows the API error message in Portuguese', async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/recipes/image`, () =>
        HttpResponse.json(
          {
            detail:
              'Não encontramos uma receita aqui — não identificamos ingredientes nem modo de preparo.',
          },
          { status: 422 },
        ),
      ),
    )

    renderAddRecipe()
    await submitPhotos('cardapio.jpg')

    expect(
      await screen.findByText(
        'Não encontramos uma receita aqui — não identificamos ingredientes nem modo de preparo.',
      ),
    ).toBeInTheDocument()
  })

  it('given the link of a recipe video, when the extraction succeeds, then it shows the same success message the other doors show', async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/recipes/video`, () =>
        HttpResponse.json(
          buildRecipe({ title: 'Bolo de cenoura do Reel', source_type: 'video' }),
          { status: 201 },
        ),
      ),
    )

    renderAddRecipe()
    await submitVideo('https://www.youtube.com/watch?v=abc123')

    expect(await screen.findByText(/Bolo de cenoura do Reel/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver receitas' })).toBeInTheDocument()
  })

  it('given a video link, when the user submits, then it goes to the video endpoint and not the link one', async () => {
    // Which door a link goes through is the user's choice: a Reel URL pasted
    // in the link field would be scraped as a page, which is not the same
    // thing at all.
    let videoRequests = 0
    let linkRequests = 0
    server.use(
      http.post(`${API_BASE_URL}/api/recipes/video`, () => {
        videoRequests += 1
        return HttpResponse.json(buildRecipe(), { status: 201 })
      }),
      http.post(`${API_BASE_URL}/api/recipes`, () => {
        linkRequests += 1
        return HttpResponse.json(buildRecipe(), { status: 201 })
      }),
    )

    renderAddRecipe()
    await submitVideo('https://www.instagram.com/reel/xyz')

    await screen.findByRole('link', { name: 'Ver receitas' })
    expect(videoRequests).toBe(1)
    expect(linkRequests).toBe(0)
  })

  it('given the video platform is blocking the server, when the user submits, then it shows the API error message in Portuguese', async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/recipes/video`, () =>
        HttpResponse.json(
          {
            detail:
              'A plataforma do vídeo está bloqueando as requisições do nosso servidor. Tente novamente mais tarde.',
          },
          { status: 503 },
        ),
      ),
    )

    renderAddRecipe()
    await submitVideo('https://www.youtube.com/watch?v=bloqueado')

    expect(
      await screen.findByText(
        'A plataforma do vídeo está bloqueando as requisições do nosso servidor. Tente novamente mais tarde.',
      ),
    ).toBeInTheDocument()
  })

  it('given a video is being read, when the request is in flight, then the loader narrates the video steps', async () => {
    // The longest wait of the three doors — metadata, then audio, then two
    // model passes — so what it says it is doing has to match what it is
    // actually doing.
    server.use(
      http.post(`${API_BASE_URL}/api/recipes/video`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50))
        return HttpResponse.json(buildRecipe(), { status: 201 })
      }),
    )

    renderAddRecipe()
    await submitVideo('https://www.youtube.com/watch?v=abc123')

    expect(await screen.findByRole('status')).toHaveTextContent('Abrindo o vídeo…')
  })

  it('given the request is in flight, when the user submits, then the button shows a loading label and is disabled', async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/recipes`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50))
        return HttpResponse.json(buildRecipe(), { status: 201 })
      }),
    )

    renderAddRecipe()
    await submitUrl('https://example.com/receita')

    expect(await screen.findByRole('button', { name: 'Extraindo receita…' })).toBeDisabled()
  })
})
