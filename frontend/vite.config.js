import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// فرانت مستقل دانشجو۳۶۰ — کامپوننت‌ها در src/app
// خروجی build به backend/static می‌رود تا FastAPI هر دو را از یک مبدأ سرو کند
export default defineConfig({
  plugins: [react()],
  css: {
    postcss: {}, // جلوگیری از خواندن postcss.config پروژه والد
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../backend/static"),
    emptyOutDir: true,
  },
});
