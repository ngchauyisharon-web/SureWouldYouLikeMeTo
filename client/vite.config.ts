import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const raw = (env.VITE_BASE_PATH ?? "").trim();
  const base = raw ? (raw.endsWith("/") ? raw : `${raw}/`) : "/";

  return {
    base,
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
