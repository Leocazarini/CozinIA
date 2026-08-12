import { Outlet } from 'react-router-dom'
import { BottomNav } from './BottomNav'

/**
 * Base layout shared by every routed screen: a persistent header, the
 * current page's content (via `Outlet`), and bottom navigation. Deliberately
 * unstyled/minimal — the final visual identity is applied later (see
 * docs/ROADMAP.md, camada 10).
 */
export function AppShell() {
  return (
    <div className="min-h-dvh bg-white text-neutral-900 pb-16">
      <header className="border-b border-neutral-200 px-4 py-3">
        <h1 className="text-lg font-semibold">Cozinia</h1>
      </header>
      <main className="px-4 py-4">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
