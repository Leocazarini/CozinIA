import { Outlet, useLocation } from 'react-router-dom'
import { BottomNav } from './BottomNav'
import { MascotPerched } from './Mascot'

/**
 * Base layout shared by every routed screen: a persistent header, the
 * current page's content (via `Outlet`), and bottom navigation.
 *
 * No background of its own — the tiled azulejo wall painted on `body`
 * shows through, which is what makes every panel read as a tile stuck
 * onto it rather than a card floating on a flat page.
 */
export function AppShell() {
  const isRecipeList = useLocation().pathname === '/'

  return (
    <div className="flex min-h-dvh flex-col text-ink">
      <header className="sticky top-0 z-10 border-b-2 border-ink bg-paper/90 backdrop-blur">
        <div className="relative mx-auto flex max-w-md items-center px-5 py-3.5">
          {/* "IA" is set as its own accent tile: the intelligence is the
              product, so the wordmark says so out loud. */}
          <h1 className="flex items-center font-display text-[1.7rem] font-extrabold leading-none tracking-[-0.035em]">
            <span>Cozin</span>
            <span className="ml-1.5 -rotate-3 rounded-[3px] border-2 border-ink bg-accent px-1.5 pt-1 pb-0.5 text-accent-ink shadow-[3px_3px_0_0_var(--color-emboss)]">
              IA
            </span>
          </h1>

          {/* The mascot lies along the header's bottom rule, watching the
              recipe list. The numbers are load-bearing: the SVG renders at
              118px (viewBox 140 wide, scale 0.843), which maps its
              transparent y=0..9.5 window exactly onto the header's 2px
              border + 6px frieze — the real line shows through the gap, so
              the dangling legs below it read as *behind* the line. Lives in
              the sticky header on purpose: it keeps lounging while the list
              scrolls past underneath. `pointer-events-none` so tiles
              scrolled under the boots stay tappable. */}
          {isRecipeList && (
            <MascotPerched className="pointer-events-none absolute right-2 bottom-[-27.8px] z-10 w-[118px]" />
          )}
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
