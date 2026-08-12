import type { ReactNode } from 'react'

interface AppShellProps {
  children: ReactNode
}

/**
 * Base page layout shared by every screen: a persistent header and a main
 * content region. Deliberately unstyled/minimal — the final visual identity
 * is applied later (see docs/ROADMAP.md, camada 10).
 */
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-dvh bg-white text-neutral-900">
      <header className="border-b border-neutral-200 px-4 py-3">
        <h1 className="text-lg font-semibold">Cozinia</h1>
      </header>
      <main className="px-4 py-4">{children}</main>
    </div>
  )
}
