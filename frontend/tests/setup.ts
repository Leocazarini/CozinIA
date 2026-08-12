// Loaded once before every test file (see vite.config.ts `test.setupFiles`).
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './mocks/server'

// Globals are off (see vite.config.ts), so Testing Library's own
// auto-cleanup (which relies on a global `afterEach`) never registers —
// unmount explicitly after every test instead.
afterEach(() => cleanup())

// Mock Service Worker intercepts every backend call made during tests —
// no test ever reaches the real API (see docs/TESTING.md).
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
