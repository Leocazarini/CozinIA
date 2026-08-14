import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { AuthProvider } from '../src/auth/AuthContext'
import { AppShell } from '../src/components/AppShell'

function renderShell(path = '/pagina') {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path={path} element={<p>conteúdo da página</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  )
}

describe('AppShell', () => {
  afterEach(() => {
    // The theme toggle writes to both — keep each test's starting theme
    // independent of whatever the previous test left behind.
    document.documentElement.removeAttribute('data-theme')
    window.localStorage.clear()
  })

  it('given a routed page, when rendered, then shows the CozinIA header and the page content inside the main landmark', () => {
    renderShell()

    expect(screen.getByRole('banner')).toHaveTextContent('CozinIA')
    expect(screen.getByRole('main')).toHaveTextContent('conteúdo da página')
  })

  it('given the app shell is rendered, when it loads, then it shows navigation links to Home and Adicionar receita', () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<p>home</p>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    )

    expect(screen.getByRole('link', { name: 'Receitas' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Adicionar' })).toBeInTheDocument()
  })

  it('given the app shell is rendered on any page, when it loads, then the CozinIA wordmark links to the home route', () => {
    renderShell('/adicionar')

    expect(screen.getByRole('link', { name: 'CozinIA' })).toHaveAttribute('href', '/')
  })

  it('given the app shell is rendered, when it loads, then it shows a button to switch to dark theme', () => {
    renderShell()

    expect(screen.getByRole('button', { name: 'Ativar tema escuro' })).toBeInTheDocument()
  })

  it('given the light theme is active, when the theme button is clicked, then it switches the page to dark theme', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: 'Ativar tema escuro' }))

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(screen.getByRole('button', { name: 'Ativar tema claro' })).toBeInTheDocument()
  })

  it('given the dark theme is active, when the theme button is clicked again, then it switches back to light theme', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: 'Ativar tema escuro' }))
    await user.click(screen.getByRole('button', { name: 'Ativar tema claro' }))

    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('given the user chose dark theme before, when the app shell is rendered again, then it keeps the dark theme', () => {
    window.localStorage.setItem('cozinia-theme', 'dark')

    renderShell()

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(screen.getByRole('button', { name: 'Ativar tema claro' })).toBeInTheDocument()
  })
})
