import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { BottomNav } from './BottomNav'
import { LogOutIcon } from './icons'
import { MascotDangling } from './Mascot'
import { ThemeToggle } from './ThemeToggle'

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
  const { signOut } = useAuth()

  return (
    <div className="flex min-h-dvh flex-col text-ink">
      {/* Installed, the app owns the whole screen (viewport-fit=cover in
          index.html), so the status bar sits *over* the top of the header
          instead of above it. The inset pushes the wordmark clear of it and
          is 0 everywhere else, including in the browser. */}
      <header
        className="sticky top-0 z-10 border-b-2 border-ink bg-paper/90 backdrop-blur"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <div className="relative mx-auto flex max-w-md items-center px-5 py-3.5">
          {/* "IA" is set as its own accent tile: the intelligence is the
              product, so the wordmark says so out loud. The tile is tucked
              *under* the word — negative margin in, "Cozin" lifted above it
              — so the two read as one mark with the urucum running behind
              the ink rather than as two words with a gap. The whole mark is
              also the way home from anywhere in the app. */}
          <Link to="/" className="flex items-center">
            <h1 className="flex items-center font-display text-[1.7rem] font-extrabold leading-none tracking-[-0.035em]">
              <span className="relative z-10">Cozin</span>
              <span className="-ml-2 -rotate-3 rounded-[3px] border-2 border-ink bg-accent px-1.5 pt-1 pb-0.5 text-accent-ink shadow-[3px_3px_0_0_var(--color-emboss)]">
                IA
              </span>
            </h1>
          </Link>

          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              onClick={signOut}
              aria-label="Sair da conta"
              className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-[3px] border-2 border-transparent text-ink-muted transition-colors after:absolute after:-inset-1.5 after:content-[''] hover:border-ink hover:bg-surface hover:text-ink"
            >
              <LogOutIcon className="h-5 w-5" />
            </button>
            <ThemeToggle />
          </div>

          {/* The mascot hangs off the header's bottom rule, over the recipe
              list. The numbers are load-bearing: the SVG renders at 106px
              (viewBox 120 wide, scale 0.883), so its transparent y=0..9.5
              window lands exactly on the header's 2px border + 6px frieze —
              the real line shows through the gap, and the body below it
              reads as hanging *from* the line. `bottom` is the artwork's own
              below-line height at that scale (77 units), which is what puts
              y=0 on the rule. Held clear of the theme toggle so the two
              never overlap. Lives in the sticky header on purpose: it keeps
              hanging there while the list scrolls past underneath.
              `pointer-events-none` so tiles behind the boots stay
              tappable. */}
          {isRecipeList && (
            <MascotDangling className="pointer-events-none absolute right-[76px] bottom-[-68px] z-10 w-[106px]" />
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
