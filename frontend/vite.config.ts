import tailwindcss from "@tailwindcss/vite";
import { readFileSync } from "node:fs";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const runtimePublicAssets = [
  {
    source: new URL(
      "./public/prototype/scarlet-character-v1.png",
      import.meta.url
    ),
    fileName: "prototype/scarlet-character-v1.png"
  },
  {
    source: new URL(
      "./public/prototype/avatar/static/motion/scarlet-startup-greeting-happyhorse-v1.mp4",
      import.meta.url
    ),
    fileName:
      "prototype/avatar/static/motion/scarlet-startup-greeting-happyhorse-v1.mp4"
  }
];

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, process.cwd(), "");

  return {
    base:
      process.env.VITE_PUBLIC_BASE_PATH ||
      environment.VITE_PUBLIC_BASE_PATH ||
      "/",
    publicDir: false,
    plugins: [
      {
        name: "scarlet-runtime-public-assets",
        buildStart() {
          for (const asset of runtimePublicAssets) {
            this.emitFile({
              type: "asset",
              fileName: asset.fileName,
              source: readFileSync(asset.source)
            });
          }
        }
      },
      react(),
      tailwindcss()
    ],
    server: {
      port: 5173,
      proxy: {
        "/api":
          process.env.VITE_API_TARGET ||
          environment.VITE_API_TARGET ||
          "http://127.0.0.1:8000",
        "/health":
          process.env.VITE_API_TARGET ||
          environment.VITE_API_TARGET ||
          "http://127.0.0.1:8000"
      }
    }
  };
});
