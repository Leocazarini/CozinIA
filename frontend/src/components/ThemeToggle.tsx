import { useTheme } from '../hooks/useTheme'
import { MoonIcon, SunIcon } from './icons'

/**
 * The icon shown is the destination, not the current state — a moon means
 * "tap to go dark", a sun means "tap to go light" — which is what the
 * accessible label spells out too.
 *
 * The tile stays 36px, because that is what the header wants; the
 * pseudo-element stretches only the *touchable* area to 48px around it, so a
 * thumb lands on it without the button growing.
 */
export function ThemeToggle() {
  const [theme, toggleTheme] = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? 'Ativar tema claro' : 'Ativar tema escuro'}
      className="relative ml-auto flex h-9 w-9 shrink-0 items-center justify-center rounded-[3px] border-2 border-transparent text-ink-muted transition-colors after:absolute after:-inset-1.5 after:content-[''] hover:border-ink hover:bg-surface hover:text-ink"
    >
      {isDark ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
    </button>
  )
}
