import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev the UI calls /api and Vite proxies to the FastAPI backend.
// In prod set VITE_API_BASE to the deployed API origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8099" },
  },
});
