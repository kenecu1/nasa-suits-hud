// The same page inside an emulated Quest 3 (acceptance 14 and 15). The emulator is `iwer`,
// installed before the page loads, so the page finds a WebXR device like on the headset.
import { createRequire } from "node:module";
import type { Page } from "@playwright/test";
import { expect, hudIsLive, PAGE, sceneIsSteady, screenshot, test, view } from "../support/fixtures";

const IWER_BUNDLE = createRequire(import.meta.url).resolve("iwer/build/iwer.min.js");

interface EmulatedHeadset {
  quaternion: { set(x: number, y: number, z: number, w: number): void };
}
type EmulatorWindow = Window & {
  IWER: {
    XRDevice: new (config: unknown) => EmulatedHeadset & { installRuntime(options: { forceInstall: boolean }): void };
    metaQuest3: unknown;
  };
  __headset: EmulatedHeadset;
};

/** Turn the emulated head about the up axis. Positive is to the wearer's left. */
async function turnHead(page: Page, degrees: number): Promise<void> {
  await page.evaluate((deg) => {
    const half = (deg * Math.PI) / 360;
    (window as unknown as EmulatorWindow).__headset.quaternion.set(0, Math.sin(half), 0, Math.cos(half));
  }, degrees);
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript({ path: IWER_BUNDLE });
  await page.addInitScript(() => {
    const w = window as unknown as EmulatorWindow;
    const headset = new w.IWER.XRDevice(w.IWER.metaQuest3);
    // Chromium has its own navigator.xr (which supports no headset here); iwer leaves a
    // native one alone unless forced (docs/notes/xr-emulation-headless-works.md).
    headset.installRuntime({ forceInstall: true });
    w.__headset = headset;
  });
});

test("Enter AR starts an immersive-ar session with the panel in view, and the panel follows a 90 degree head turn", async ({
  page,
  backend: _backend,
}, testInfo) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  expect((await view(page)).presenting).toBe(false);

  await page.getByRole("button", { name: "Enter AR" }).click();
  await expect.poll(async () => (await view(page)).presenting, { timeout: 15_000 }).toBe(true);
  expect((await view(page)).xrMode).toBe("immersive-ar");
  // The start bar is HTML and must be gone: nothing in the headset view is HTML.
  await expect(page.getByRole("button", { name: "Enter AR" })).toHaveCount(0);

  await expect.poll(async () => (await view(page)).panelInView).toBe(true);
  const facingFront = await view(page);
  expect(Math.abs(facingFront.headYawDeg)).toBeLessThan(1);
  expect(Math.abs(facingFront.rigYawDeg)).toBeLessThan(1);
  await sceneIsSteady(page);
  await screenshot(page, testInfo, "in-session");

  const outOfViewBefore = (await view(page)).framesOutOfView;
  await turnHead(page, 90);
  // The page's own camera reports the turn: the emulated head really moved.
  await expect.poll(async () => Math.round((await view(page)).headYawDeg), { timeout: 5000 }).toBe(90);

  await page.waitForTimeout(2000);
  const afterTurn = await view(page);
  expect(afterTurn.panelInView, "2 s after the turn the panel is back in view").toBe(true);
  expect(Math.abs(afterTurn.rigYawDeg - 90)).toBeLessThan(2);
  // The rig follows with a delay: right after the turn the panel was out of view for a while.
  expect(afterTurn.framesOutOfView).toBeGreaterThan(outOfViewBefore);

  console.log(`draw calls, emulated headset: ${afterTurn.maxDrawCalls}`);
  expect(afterTurn.maxDrawCalls).toBeGreaterThan(0);
  expect(afterTurn.maxDrawCalls).toBeLessThanOrEqual(50);
});
