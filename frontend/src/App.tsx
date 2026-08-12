import { AppShell } from './components/AppShell'

// Screens are wired into the main content region in later layers
// (camada 7 onward — see docs/ROADMAP.md).
export function App() {
  return <AppShell>{null}</AppShell>
}
