// Dev server and unit tests for the client.
// The page talks to the backend through its own origin: /ws and /health are forwarded to the
// backend on SUITS_PORT (default 8000), so a headset needs only the page's address.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// `||`, not `??`: an empty variable means "not set", and Number("") would be port 0.
const backendPort = process.env.SUITS_PORT || "8000";
const clientPort = Number(process.env.SUITS_CLIENT_PORT || "5173");
if (!Number.isInteger(clientPort)) throw new Error(`SUITS_CLIENT_PORT must be a port number, got "${process.env.SUITS_CLIENT_PORT}"`);

export default defineConfig({
  plugins: [react()],
  resolve: {
    // One three.js for everything. The emulator's control panel (@iwer/devui) asks for an older
    // copy of its own, but shares helper packages with the app; two copies mixed crash it.
    dedupe: ["three"],
  },
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
      "iwer",
      "@iwer/devui",
    ],
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
