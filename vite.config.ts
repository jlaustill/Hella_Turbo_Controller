import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  base: "./",
  build: {
    outDir: "dist",
    assetsDir: "assets",
    rollupOptions: {
      external: [],
      output: {
        assetFileNames: (assetInfo) => {
          if (
            assetInfo.name &&
            assetInfo.name.endsWith(".js") &&
            assetInfo.name.includes("worker")
          ) {
            return "workers/[name].[ext]";
          }
          return "assets/[name]-[hash].[ext]";
        },
      },
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  worker: {
    format: "es",
  },
});
