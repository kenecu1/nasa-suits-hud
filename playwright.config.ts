// End-to-end tests: the real page against the real backend in sim mode.
// Two projects: `desktop` (the laptop page) and `xr` (the same page inside an emulated Quest 3).
// The tests start and stop the backend themselves (e2e/support/backend.ts); only the client dev
// server is started here. Ports differ from `npm run dev`, so both can run at the same time.
import { defineConfig } from "@playwright/test";
import { BACKEND_PORT, CLIENT_PORT } from "./e2e/support/ports";

export default defineConfig({
  testDir: "e2e",
  // One backend, and one test stops it: never run tests side by side.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 60_000,
  outputDir: "test-results",
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],

  // Screenshot baselines are committed for Windows only (CLAUDE.md, Testing). Elsewhere the
  // comparison is off; the tests still save their screenshots to test-results/.
  ignoreSnapshots: process.platform !== "win32",
  snapshotPathTemplate: "e2e/screenshots/{projectName}/{arg}-{platform}{ext}",
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },

  use: {
    baseURL: `http://localhost:${CLIENT_PORT}`,
    viewport: { width: 1280, height: 720 },
    trace: "retain-on-failure",
    launchOptions: {
      // WebGL without a GPU: the same software renderer on every machine and in CI.
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
    },
  },

  webServer: {
    command: "npm run dev --workspace client",
    url: `http://localhost:${CLIENT_PORT}`,
    env: { SUITS_PORT: String(BACKEND_PORT), SUITS_CLIENT_PORT: String(CLIENT_PORT) },
    reuseExistingServer: false,
    timeout: 60_000,
  },

  projects: [
    { name: "desktop", testDir: "e2e/desktop" },
    { name: "xr", testDir: "e2e/xr" },
  ],
});
