import { type FormEvent, useState } from 'react'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'

const BUTTON_CLASS =
  'tile tile-flat tile-pressable bg-accent py-3.5 font-display text-sm font-extrabold tracking-[0.14em] text-accent-ink uppercase disabled:opacity-55'

/**
 * The one screen shown when nobody is signed in. On success the AuthProvider
 * flips the app over to the real routes; there is no sign-up — accounts are
 * created by the operator (see backend/app/cli.py).
 */
export function Login() {
  const { signIn } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await signIn(username, password)
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'Não foi possível entrar. Verifique sua conexão e tente novamente.',
      )
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-10 text-ink">
      <form
        onSubmit={handleSubmit}
        className="tile w-full max-w-sm bg-surface p-6"
        aria-labelledby="login-title"
      >
        <h1 id="login-title" className="font-display text-2xl font-extrabold text-ink">
          CozinIA
        </h1>
        <p className="mt-1 mb-6 text-sm text-ink-muted">Entre para ver e salvar suas receitas.</p>

        <label className="mb-1 block font-display text-xs font-extrabold tracking-[0.12em] text-ink-muted uppercase">
          Usuário
        </label>
        <input
          type="text"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          disabled={submitting}
          className="field mb-4 w-full px-4 py-3 text-sm"
        />

        <label className="mb-1 block font-display text-xs font-extrabold tracking-[0.12em] text-ink-muted uppercase">
          Senha
        </label>
        <input
          type="password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={submitting}
          className="field mb-5 w-full px-4 py-3 text-sm"
        />

        {error !== null && (
          <p role="alert" className="mb-4 border-l-4 border-accent pl-3 text-sm font-medium text-ink">
            {error}
          </p>
        )}

        <button type="submit" disabled={submitting} className={`${BUTTON_CLASS} w-full`}>
          {submitting ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}
