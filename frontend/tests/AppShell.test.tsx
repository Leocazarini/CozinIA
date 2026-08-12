import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppShell } from '../src/components/AppShell'

describe('AppShell', () => {
  it('given a routed page, when rendered, then shows the CozinIA header and the page content inside the main landmark', () => {
    render(
      <MemoryRouter initialEntries={['/pagina']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/pagina" element={<p>conteúdo da página</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('banner')).toHaveTextContent('CozinIA')
    expect(screen.getByRole('main')).toHaveTextContent('conteúdo da página')
  })

  it('given the app shell is rendered, when it loads, then it shows navigation links to Home and Adicionar receita', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<p>home</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Receitas' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Adicionar' })).toBeInTheDocument()
  })
})
