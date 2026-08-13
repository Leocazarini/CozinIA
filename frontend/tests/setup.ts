// Loaded once before every test file (see vite.config.ts `test.setupFiles`).
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './mocks/server'

// Globals are off (see vite.config.ts), so Testing Library's own
// auto-cleanup (which relies on a global `afterEach`) never registers —
// unmount explicitly after every test instead.
afterEach(() => cleanup())

// jsdom implements neither of these, and the photo picker uses them to
// preview the images the user just chose. Stubbed globally rather than
// per-test: it's a gap in the environment, not behaviour under test.
URL.createObjectURL = () => 'blob:preview'
URL.revokeObjectURL = () => {}

// Mock Service Worker intercepts every backend call made during tests —
// no test ever reaches the real API (see docs/TESTING.md).
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
