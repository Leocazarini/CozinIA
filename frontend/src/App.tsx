import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './api/queryClient'
import { AppShell } from './components/AppShell'
import { Home } from './pages/Home'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell>
        <Home />
      </AppShell>
    </QueryClientProvider>
  )
}
