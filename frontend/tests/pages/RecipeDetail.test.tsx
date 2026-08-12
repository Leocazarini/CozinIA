import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API_BASE_URL } from '../../src/api/config'
import type { Recipe } from '../../src/api/types'
import { RecipeDetail } from '../../src/pages/RecipeDetail'
import { buildRecipe } from '../factories/recipe'
import { server } from '../mocks/server'

const RECIPE_ID = '11111111-1111-1111-1111-111111111111'

function renderRecipeDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/recipes/${RECIPE_ID}`]}>
        <Routes>
          <Route path="/recipes/:id" element={<RecipeDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RecipeDetail', () => {
  it('given a saved recipe, when the page loads, then it shows the title, ingredients and steps', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes/${RECIPE_ID}`, () =>
        HttpResponse.json(
          buildRecipe({
            id: RECIPE_ID,
            title: 'Bolo de cenoura',
            ingredients: [{ name: 'Cenoura', quantity: '3', unit: 'unidades', notes: null }],
            steps: [{ order: 1, text: 'Bata tudo no liquidificador.' }],
          }),
        ),
      ),
    )

    renderRecipeDetail()

    expect(await screen.findByRole('heading', { name: 'Bolo de cenoura' })).toBeInTheDocument()
    expect(screen.getByText(/Cenoura/)).toBeInTheDocument()
    expect(screen.getByText('Bata tudo no liquidificador.')).toBeInTheDocument()
  })

  it('given no recipe exists with that id, when the page loads, then it shows the API not-found message', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes/${RECIPE_ID}`, () =>
        HttpResponse.json({ detail: 'Receita não encontrada.' }, { status: 404 }),
      ),
    )

    renderRecipeDetail()

    expect(await screen.findByText('Receita não encontrada.')).toBeInTheDocument()
  })

  it('given the user edits the title and saves, when the update succeeds, then it shows the updated title and leaves edit mode', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes/${RECIPE_ID}`, () =>
        HttpResponse.json(buildRecipe({ id: RECIPE_ID, title: 'Bolo de cenoura' })),
      ),
      http.patch(`${API_BASE_URL}/api/recipes/${RECIPE_ID}`, async ({ request }) => {
        const changes = (await request.json()) as Partial<Recipe>
        return HttpResponse.json(buildRecipe({ id: RECIPE_ID, ...changes }))
      }),
    )

    const user = userEvent.setup()
    renderRecipeDetail()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))

    const titleInput = screen.getByLabelText('Título')
    await user.clear(titleInput)
    await user.type(titleInput, 'Bolo de cenoura da vovó')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(
      await screen.findByRole('heading', { name: 'Bolo de cenoura da vovó' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Editar' })).toBeInTheDocument()
  })

  it('given the user adds an ingredient and saves, when the update succeeds, then the new ingredient is shown', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes/${RECIPE_ID}`, () =>
        HttpResponse.json(buildRecipe({ id: RECIPE_ID, ingredients: [] })),
      ),
      http.patch(`${API_BASE_URL}/api/recipes/${RECIPE_ID}`, async ({ request }) => {
        const changes = (await request.json()) as Partial<Recipe>
        return HttpResponse.json(buildRecipe({ id: RECIPE_ID, ...changes }))
      }),
    )

    const user = userEvent.setup()
    renderRecipeDetail()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))
    await user.click(screen.getByRole('button', { name: 'Adicionar ingrediente' }))
    await user.type(screen.getByLabelText('Nome do ingrediente 1'), 'Farinha')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('Farinha')).toBeInTheDocument()
  })

  it('given the user is editing, when they click cancelar, then it discards changes and returns to view mode', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/recipes/${RECIPE_ID}`, () =>
        HttpResponse.json(buildRecipe({ id: RECIPE_ID, title: 'Bolo de cenoura' })),
      ),
    )

    const user = userEvent.setup()
    renderRecipeDetail()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))
    const titleInput = screen.getByLabelText('Título')
    await user.clear(titleInput)
    await user.type(titleInput, 'Rascunho descartado')
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(await screen.findByRole('heading', { name: 'Bolo de cenoura' })).toBeInTheDocument()
  })
})
