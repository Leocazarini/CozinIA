import { Outlet } from 'react-router-dom'
import { BottomNav } from './BottomNav'

/**
 * Base layout shared by every routed screen: a persistent header, the
 * current page's content (via `Outlet`), and bottom navigation.
 *
 * No background of its own — the tiled azulejo wall painted on `body`
 * shows through, which is what makes every panel read as a tile stuck
 * onto it rather than a card floating on a flat page.
 */
export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col text-ink">
      <header className="sticky top-0 z-10 border-b-2 border-ink bg-paper/90 backdrop-blur">
        <div className="mx-auto flex max-w-md items-center px-5 py-3.5">
          {/* "IA" is set as its own accent tile: the intelligence is the
              product, so the wordmark says so out loud. */}
          <h1 className="flex items-center font-display text-[1.7rem] font-extrabold leading-none tracking-[-0.035em]">
            <span>Cozin</span>
            <span className="ml-1.5 -rotate-3 rounded-[3px] border-2 border-ink bg-accent px-1.5 pt-1 pb-0.5 text-accent-ink shadow-[3px_3px_0_0_var(--color-emboss)]">
              IA
            </span>
          </h1>
        </div>
      </header>
      <div className="frieze" aria-hidden="true" />
      <main className="mx-auto w-full max-w-md flex-1 px-5 py-7 pb-32">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
