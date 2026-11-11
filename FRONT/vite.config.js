import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Puerto 5173: coincide con CORS_ORIGINS del backend (.env.example)
export default defineConfig({ plugins: [react()], server: { host: true, port: 5173, strictPort: true } });
