import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/audit/",
  server: {
    port: 5174,
    proxy: {
      "/audit/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/audit/, ""),
      },
    },
  },
});
