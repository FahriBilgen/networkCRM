import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  server: {
    port: 4173,
    strictPort: true,
    proxy: {
      "/api": "http://localhost:8000"
    }
  },
  build: {
    sourcemap: true,
    outDir: resolve(__dirname, "../../../demo_build/ui_dist"),
    emptyOutDir: true,
  }
});
