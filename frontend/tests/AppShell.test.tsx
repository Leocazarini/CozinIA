import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AppShell } from '../src/components/AppShell'

describe('AppShell', () => {
  it('given page content as children, when rendered, then shows the Cozinia header and the content inside the main landmark', () => {
    render(
      <AppShell>
        <p>conteúdo da página</p>
      </AppShell>,
    )

    expect(screen.getByRole('banner')).toHaveTextContent('Cozinia')
    expect(screen.getByRole('main')).toHaveTextContent('conteúdo da página')
  })
})
