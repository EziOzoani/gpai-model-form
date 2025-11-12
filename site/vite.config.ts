import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  // Configure base URL for GitHub Pages deployment
  // Repository name: gpai-model-form
  base: mode === "production" ? "/gpai-model-form/" : "/",
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Build configuration for GitHub Pages
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
  },
}));
