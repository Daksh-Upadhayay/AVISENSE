import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  // Fixed port so the backend's ALLOWED_ORIGINS and Supabase's Site URL stay valid.
  server: { port: 5180, strictPort: true },
})
