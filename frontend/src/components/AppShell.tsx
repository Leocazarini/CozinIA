import { Outlet } from 'react-router-dom'
import { BottomNav } from './BottomNav'

/**
 * Base layout shared by every routed screen: a persistent header, the
 * current page's content (via `Outlet`), and bottom navigation.
 */
export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-paper text-ink">
      <header className="sticky top-0 z-10 border-b border-line bg-paper/95 px-5 py-4 backdrop-blur">
        <h1 className="font-display text-2xl italic tracking-tight">Cozinia</h1>
      </header>
      <main className="mx-auto w-full max-w-md flex-1 px-5 py-6 pb-28">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
