import { NavLink } from 'react-router-dom'
import { BookIcon, PlusIcon } from './icons'

function navLinkClassName({ isActive }: { isActive: boolean }) {
  return [
    'flex flex-1 flex-col items-center gap-1 py-2.5 text-xs tracking-wide transition-colors',
    isActive ? 'text-accent' : 'text-ink-muted hover:text-ink',
  ].join(' ')
}

/** Mobile-first bottom tab bar — the app's only navigation between screens. */
export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 border-t border-line bg-paper/95 backdrop-blur"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="mx-auto flex max-w-md">
        <NavLink to="/" end className={navLinkClassName}>
          <BookIcon className="h-5 w-5" />
          Receitas
        </NavLink>
        <NavLink to="/adicionar" className={navLinkClassName}>
          <PlusIcon className="h-5 w-5" />
          Adicionar
        </NavLink>
      </div>
    </nav>
  )
}
