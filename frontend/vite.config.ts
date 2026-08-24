import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/analyze-building": "http://127.0.0.1:8000",
      "/city-analysis": "http://127.0.0.1:8000",
      "/optimization-routes": "http://127.0.0.1:8000",
      "/predict-solar": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/status": "http://127.0.0.1:8000",
      "/locations": "http://127.0.0.1:8000",
      "/sample-areas": "http://127.0.0.1:8000",
      "/area": "http://127.0.0.1:8000",
      "/ai": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: undefined, // Let Vite auto-split
      },
    },
  },
  preview: {
    port: 3000,
  },
});
