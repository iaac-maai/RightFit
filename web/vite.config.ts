import { cloudflare } from "@cloudflare/vite-plugin";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The page (React) and the Worker build together; `npm run dev` runs both, with D1 on the laptop
export default defineConfig({ plugins: [react(), cloudflare()] });
