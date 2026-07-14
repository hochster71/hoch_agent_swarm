import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // HELM LIVE truth wall (backend.helm_live_api on :8770) — more specific than /api
      "/api/helm": {
        target: "http://127.0.0.1:8770",
        changeOrigin: true,
      },
      "/api/v1/helm": {
        target: "http://127.0.0.1:8770",
        changeOrigin: true,
      },
      "/api/founder": {
        target: "http://127.0.0.1:8770",
        changeOrigin: true,
      },
      // Live PERT / founder walls served by helm_live_api (not the Vite SPA shell)
      "/pert": {
        target: "http://127.0.0.1:8770",
        changeOrigin: true,
      },
      "/founder": {
        target: "http://127.0.0.1:8770",
        changeOrigin: true,
      },
      // Main HAS backend (council, control-plane status, etc.)
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
