// Shared test setup: a running backend for every test, and helpers to read window.__hud.
import { test as base, expect, type Page, type TestInfo } from "@playwright/test";
import type { HudHook, HudView } from "../../client/src/testHook";
import { Backend } from "./backend";
import { BACKEND_PORT } from "./ports";

export { expect };
export type { Page };

/** The page with the built-in emulator panel off (client/src/scene/xr.ts). */
export const PAGE = "/?emulator=off";

export const test = base.extend<{ backend: Backend }, { backendPort: number; backendProcess: Backend }>({
  backendPort: [BACKEND_PORT, { option: true, scope: "worker" }],
  backendProcess: [
    async ({ backendPort }, use) => {
      const backend = new Backend(backendPort);
      await use(backend);
      await backend.stop();
    },
    { scope: "worker" },
  ],
  // Every test starts with the backend up, even if the one before left it stopped.
  backend: async ({ backendProcess }, use) => {
    await backendProcess.start();
    await use(backendProcess);
  },
});

export function hud(page: Page): Promise<HudHook> {
  return page.evaluate(() => window.__hud);
}

export async function view(page: Page): Promise<HudView> {
  const current = (await hud(page)).view;
  if (current === null) throw new Error("the scene has not drawn a frame yet");
  return current;
}

/** Wait until the page shows live data and the scene has settled (fonts loaded, text drawn). */
export async function hudIsLive(page: Page): Promise<void> {
  await expect.poll(async () => (await hud(page)).conn, { timeout: 15_000 }).toBe("live");
  await sceneIsSteady(page);
}

/** The draw-call count has stopped changing: nothing is still loading into the scene. */
export async function sceneIsSteady(page: Page): Promise<void> {
  await page.waitForFunction(
    () => {
      const w = window as unknown as { __steady?: { calls: number; since: number } };
      const v = window.__hud?.view;
      if (!v || v.drawCalls === 0) return false;
      if (!w.__steady || w.__steady.calls !== v.drawCalls) w.__steady = { calls: v.drawCalls, since: v.frames };
      return v.frames - w.__steady.since >= 30;
    },
    undefined,
    { timeout: 20_000, polling: 100 },
  );
}

/**
 * Save a screenshot with the test's results (always), and compare it with the committed
 * baseline (Windows only; see playwright.config.ts).
 */
export async function screenshot(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path });
  await testInfo.attach(name, { path, contentType: "image/png" });
  await expect(page).toHaveScreenshot(`${name}.png`);
}
