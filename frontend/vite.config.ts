import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Forward /api calls to the FastAPI backend so the frontend only uses relative URLs.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
