import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// EV Pal frontend — Vite config.
// Proxies /api/* to the FastAPI backend so the frontend never needs to
// hardcode a backend origin (works the same in dev and behind a reverse
// proxy later).
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
