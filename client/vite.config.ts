// Dev server and unit tests for the client.
// The page talks to the backend through its own origin: /ws and /health are forwarded to the
// backend on SUITS_PORT (default 8000), so a headset needs only the page's address.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const backendPort = process.env.SUITS_PORT ?? "8000";
const clientPort = Number(process.env.SUITS_CLIENT_PORT ?? "5173");

export default defineConfig({
  plugins: [react()],
  server: {
    port: clientPort,
    strictPort: true,
    proxy: {
      "/ws": { target: `ws://127.0.0.1:${backendPort}`, ws: true },
      "/health": { target: `http://127.0.0.1:${backendPort}` },
    },
  },
  optimizeDeps: {
    // Named up front so the dev server does not find them mid-test and reload the page.
    include: [
      "react",
      "react-dom/client",
      "three",
      "zustand",
      "@react-three/fiber",
      "@react-three/xr",
      "@react-three/uikit",
      "@pmndrs/msdfonts/inter",
    ],
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
