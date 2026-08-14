import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { App } from '../src/App'

describe('App', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('given nobody is signed in, when the app loads, then it redirects to /login and shows none of the app', () => {
    window.history.pushState({}, '', '/')

    render(<App />)

    expect(window.location.pathname).toBe('/login')
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
    expect(screen.queryByRole('banner')).not.toBeInTheDocument()
  })

  it('given a stored session, when the app loads, then it shows the CozinIA header inside the base layout', () => {
    localStorage.setItem('cozinia-token', 'a-stored-token')

    render(<App />)

    expect(screen.getByRole('banner')).toHaveTextContent('CozinIA')
    expect(screen.getByRole('main')).toBeInTheDocument()
  })
})
