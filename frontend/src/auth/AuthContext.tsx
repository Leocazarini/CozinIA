import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { login as apiLogin, logout as apiLogout } from '../api/auth'
import { getToken } from '../api/authToken'
import { setUnauthorizedHandler } from '../api/client'

interface AuthState {
  /** Present when signed in. The app is gated on this, not on its contents. */
  token: string | null
  signIn: (username: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken())

  // When any API call comes back 401 (an expired token), drop the session so
  // the app falls back to the login screen.
  useEffect(() => {
    setUnauthorizedHandler(() => setTokenState(null))
    return () => setUnauthorizedHandler(null)
  }, [])

  const signIn = useCallback(async (username: string, password: string) => {
    await apiLogin(username, password)
    setTokenState(getToken())
  }, [])

  const signOut = useCallback(() => {
    apiLogout()
    setTokenState(null)
  }, [])

  const value = useMemo<AuthState>(() => ({ token, signIn, signOut }), [token, signIn, signOut])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components -- context hook colocated with its provider by design
export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
