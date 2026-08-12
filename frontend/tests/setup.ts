// Loaded once before every test file (see vite.config.ts `test.setupFiles`).
import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './mocks/server'

// Mock Service Worker intercepts every backend call made during tests —
// no test ever reaches the real API (see docs/TESTING.md).
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
