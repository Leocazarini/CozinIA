import { NavLink } from 'react-router-dom'
import { BookIcon, PlusIcon } from './icons'

function navLinkClassName({ isActive }: { isActive: boolean }) {
  return [
    'group flex flex-1 flex-col items-center gap-1.5 py-3 font-display text-[0.7rem] font-bold uppercase tracking-[0.12em] transition-colors',
    isActive ? 'text-accent' : 'text-ink-muted hover:text-ink',
  ].join(' ')
}

/** The icon sits in its own little tile, filled with urucum when active. */
function tileClassName(isActive: boolean) {
  return [
    'flex h-9 w-9 items-center justify-center rounded-[3px] border-2 transition-all duration-150',
    isActive
      ? 'border-ink bg-accent text-accent-ink shadow-[3px_3px_0_0_var(--color-emboss)]'
      : 'border-transparent bg-transparent group-hover:border-ink group-hover:bg-surface',
  ].join(' ')
}

/** Mobile-first bottom tab bar — the app's only navigation between screens. */
export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 border-t-2 border-ink bg-paper/95 backdrop-blur"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="mx-auto flex max-w-md">
        <NavLink to="/" end className={navLinkClassName}>
          {({ isActive }) => (
            <>
              <span className={tileClassName(isActive)}>
                <BookIcon className="h-5 w-5" />
              </span>
              Receitas
            </>
          )}
        </NavLink>
        <NavLink to="/adicionar" className={navLinkClassName}>
          {({ isActive }) => (
            <>
              <span className={tileClassName(isActive)}>
                <PlusIcon className="h-5 w-5" />
              </span>
              Adicionar
            </>
          )}
        </NavLink>
      </div>
    </nav>
  )
}
