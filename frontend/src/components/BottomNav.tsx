import { NavLink } from 'react-router-dom'

const linkClassName = ({ isActive }: { isActive: boolean }) =>
  `flex-1 py-3 text-center text-sm ${isActive ? 'font-semibold text-neutral-900' : 'text-neutral-500'}`

/** Mobile-first bottom tab bar — the app's only navigation between screens. */
export function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 flex border-t border-neutral-200 bg-white">
      <NavLink to="/" end className={linkClassName}>
        Receitas
      </NavLink>
      <NavLink to="/adicionar" className={linkClassName}>
        Adicionar
      </NavLink>
    </nav>
  )
}
