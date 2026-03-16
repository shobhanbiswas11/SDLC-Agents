import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/run-agent': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
    }
  }
})