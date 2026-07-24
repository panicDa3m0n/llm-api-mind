import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: process.env.VITE_PUBLIC_BASE_PATH || "/",
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_TARGET || "http://127.0.0.1:8000",
      "/health": process.env.VITE_API_TARGET || "http://127.0.0.1:8000"
    }
  }
});
