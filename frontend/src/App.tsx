import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { queryClient } from './api/queryClient'
import { AppShell } from './components/AppShell'
import { AddRecipe } from './pages/AddRecipe'
import { Home } from './pages/Home'
import { RecipeDetail } from './pages/RecipeDetail'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<Home />} />
            <Route path="/adicionar" element={<AddRecipe />} />
            <Route path="/recipes/:id" element={<RecipeDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
