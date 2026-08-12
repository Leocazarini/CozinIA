import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API_BASE_URL } from '../../src/api/config'
import { Home } from '../../src/pages/Home'
import { buildRecipe } from '../factories/recipe'
import { server } from '../mocks/server'

function renderHome() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Home', () => {
  it('given the API has saved recipes, when Home renders, then it lists each recipe title', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes`, () =>
        HttpResponse.json([
          buildRecipe({ id: '1', title: 'Bolo de cenoura' }),
          buildRecipe({ id: '2', title: 'Feijoada' }),
        ]),
      ),
    )

    renderHome()

    expect(await screen.findByText('Bolo de cenoura')).toBeInTheDocument()
    expect(screen.getByText('Feijoada')).toBeInTheDocument()
  })

  it('given the API has saved recipes, when Home renders, then each title links to its detail page', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes`, () =>
        HttpResponse.json([buildRecipe({ id: '1', title: 'Bolo de cenoura' })]),
      ),
    )

    renderHome()

    const link = await screen.findByRole('link', { name: 'Bolo de cenoura' })
    expect(link).toHaveAttribute('href', '/recipes/1')
  })

  it('given the API has no saved recipes, when Home renders, then it shows the empty-state message in Portuguese', async () => {
    server.use(http.get(`${API_BASE_URL}/api/recipes`, () => HttpResponse.json([])))

    renderHome()

    expect(await screen.findByText('Nenhuma receita salva ainda.')).toBeInTheDocument()
  })

  it('given the API request fails, when Home renders, then it shows an error message in Portuguese', async () => {
    server.use(http.get(`${API_BASE_URL}/api/recipes`, () => HttpResponse.error()))

    renderHome()

    expect(
      await screen.findByText('Não foi possível carregar as receitas. Tente novamente.'),
    ).toBeInTheDocument()
  })

  it('given the API is still responding, when Home renders, then it shows a loading message', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50))
        return HttpResponse.json([])
      }),
    )

    renderHome()

    expect(screen.getByText('Carregando receitas…')).toBeInTheDocument()
  })
})
