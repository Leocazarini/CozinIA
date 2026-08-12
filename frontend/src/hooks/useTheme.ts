import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'cozinia-theme'

function isTheme(value: string | null): value is Theme {
  return value === 'light' || value === 'dark'
}

/** The user's last explicit choice, if any — read once, outside React state. */
function getStoredTheme(): Theme | null {
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return isTheme(stored) ? stored : null
}

/**
 * Falls back to the OS preference when the user hasn't chosen yet.
 * `matchMedia` isn't implemented by jsdom, so this guards rather than
 * crashing the test environment.
 */
function getSystemTheme(): Theme {
  if (typeof window.matchMedia !== 'function') {
    return 'light'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Tracks the active theme and mirrors it onto `<html data-theme>`, which is
 * what `index.css` keys its dark-mode tokens off (see the CSS for the
 * explicit-choice-beats-system-preference cascade). Persists every change
 * to `localStorage` so a reload keeps the user's last choice.
 */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme() ?? getSystemTheme())

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  function toggleTheme() {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
  }

  return [theme, toggleTheme]
}
