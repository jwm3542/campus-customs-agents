import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The board runs on :5173; the FastAPI backend (CORS allows this origin) runs on :8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
