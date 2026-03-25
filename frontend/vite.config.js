import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    // Used when VITE_API_BASE_URL is unset: browser hits same origin, Vite forwards these paths to the API.
    // If you set VITE_API_BASE_URL in .env.local, main.js calls the API directly (CORS on FastAPI).
    proxy: {
      "/invoices": "http://127.0.0.1:8000",
      "/policy": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
