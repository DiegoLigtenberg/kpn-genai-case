import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/invoices": "http://127.0.0.1:8000",
      "/policy": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
