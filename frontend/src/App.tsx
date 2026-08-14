import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { queryClient } from './api/queryClient'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { AppShell } from './components/AppShell'
import { AddRecipe } from './pages/AddRecipe'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { RecipeDetail } from './pages/RecipeDetail'

/**
 * Gate: with no session, every route redirects to /login (so the address bar
 * actually reads /login, not the page the user asked for). Once signed in,
 * /login redirects back to home and the real routes mount.
 */
function AuthGate() {
  const { token } = useAuth()

  if (token === null) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route element={<AppShell />}>
        <Route path="/" element={<Home />} />
        <Route path="/adicionar" element={<AddRecipe />} />
        <Route path="/recipes/:id" element={<RecipeDetail />} />
      </Route>
    </Routes>
  )
}

export function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthGate />
        </BrowserRouter>
      </QueryClientProvider>
    </AuthProvider>
  )
}
