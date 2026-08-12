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

async function submitUrl(url: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Link da receita'), url)
  await user.click(screen.getByRole('button', { name: 'Adicionar receita' }))
}

describe('AddRecipe', () => {
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
