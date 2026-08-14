/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'
// Extension included on purpose: Vite's native config loader cannot resolve
// an extensionless TypeScript import here.
import { pwaOptions } from './pwa.config.ts'

// Where the dev server forwards /api and /health. Inside the compose network
// that is the backend service; running `npm run dev` straight on the host it
// is the port compose publishes.
const DEV_API_PROXY = process.env.VITE_DEV_API_PROXY || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), VitePWA(pwaOptions)],
  server: {
    host: true,
    // Mirrors what nginx does in production (see frontend/nginx/), so the app
    // talks to one origin in both: no CORS, no mixed content, and no code
    // path that only exists in development.
    proxy: {
      '/api': { target: DEV_API_PROXY, changeOrigin: true },
      '/health': { target: DEV_API_PROXY, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
  },
})
