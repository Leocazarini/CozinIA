import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from '../src/App'

describe('App', () => {
  it('given the app is rendered, when it loads, then it shows the Cozinia header inside the base layout', () => {
    render(<App />)

    expect(screen.getByRole('banner')).toHaveTextContent('Cozinia')
    expect(screen.getByRole('main')).toBeInTheDocument()
  })
})
