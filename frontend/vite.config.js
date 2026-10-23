import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Where the dev server forwards /api and /uploads. Inside docker compose the
// backend container is reachable as "backend"; running `npm run dev` on the
// host, set API_PROXY_TARGET=http://localhost:8000.
const apiTarget = process.env.API_PROXY_TARGET || 'http://backend:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      // Local-fallback uploads served by FastAPI StaticFiles (MEDIA_BACKEND=local).
      '/uploads': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
