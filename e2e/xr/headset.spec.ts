// The same page inside an emulated Quest 3 (acceptance 14 and 15). The emulator is `iwer`,
// installed before the page loads, so the page finds a WebXR device like on the headset.
import { createRequire } from "node:module";
import type { Page } from "@playwright/test";
import { expect, hud, hudIsLive, PAGE, sceneIsSteady, screenshot, test, view } from "../support/fixtures";

const IWER_BUNDLE = createRequire(import.meta.url).resolve("iwer/build/iwer.min.js");

interface EmulatedController {
  connected: boolean;
  updateButtonValue(id: string, value: number): void;
}

interface EmulatedHeadset {
  quaternion: { set(x: number, y: number, z: number, w: number): void };
  primaryInputMode: "controller" | "hand";
  controllers: { left?: EmulatedController; right?: EmulatedController };
}
type EmulatorWindow = Window & {
  IWER: {
    XRDevice: new (config: unknown) => EmulatedHeadset & { installRuntime(options: { forceInstall: boolean }): void };
    metaQuest3: unknown;
  };
  __headset: EmulatedHeadset;
  /** What the page asked the emulated device for, and the session it was given. */
  __requestedMode?: string;
  __session?: { environmentBlendMode?: string };
};

/** Turn the emulated head about the up axis. Positive is to the wearer's left. */
async function turnHead(page: Page, degrees: number): Promise<void> {
  await page.evaluate((deg) => {
    const half = (deg * Math.PI) / 360;
    (window as unknown as EmulatorWindow).__headset.quaternion.set(0, Math.sin(half), 0, Math.cos(half));
  }, degrees);
}

/** Press and release a button on the emulated right controller, a few frames apart. */
async function pressButton(page: Page, button: string): Promise<void> {
  const set = (value: number) =>
    page.evaluate(
      ([id, v]) => (window as unknown as EmulatorWindow).__headset.controllers.right?.updateButtonValue(id, v),
      [button, value] as const,
    );
  await set(1);
  await page.waitForTimeout(300);
  await set(0);
  await page.waitForTimeout(300);
}

async function enterAr(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Enter AR" }).click();
  await expect.poll(async () => (await view(page)).presenting, { timeout: 15_000 }).toBe(true);
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
    // Record the request the device itself receives, not what the page says it asked for.
    const { xr } = navigator as unknown as {
      xr: { requestSession(mode: string, init?: unknown): Promise<{ environmentBlendMode?: string }> };
    };
    const request = xr.requestSession.bind(xr);
    xr.requestSession = (mode, init) => {
      w.__requestedMode = mode;
      return request(mode, init).then((session) => {
        w.__session = session;
        return session;
      });
    };
  });
});

test("Enter AR starts an immersive-ar session with the panel in view, and the panel follows a 90 degree head turn", async ({
  page,
  backend: _backend,
}, testInfo) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  expect((await view(page)).presenting).toBe(false);

  await enterAr(page);
  expect((await view(page)).xrMode).toBe("immersive-ar");
  // The emulated device was asked for AR and gave a see-through session.
  const granted = await page.evaluate(() => {
    const w = window as unknown as EmulatorWindow;
    return { mode: w.__requestedMode, blend: w.__session?.environmentBlendMode };
  });
  expect(granted).toEqual({ mode: "immersive-ar", blend: "alpha-blend" });
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
  expect(afterTurn.maxDrawCalls).toBeLessThanOrEqual(100);
});

test("inside the session the view models match the laptop's, and the controller's A and B buttons fire ack_alert and toggle_details", async ({
  page,
  backend,
}, testInfo) => {
  await backend.start({ mode: "sim", scenario: "fan_failure", speed: 10 });
  await page.goto(PAGE);
  await hudIsLive(page);
  await enterAr(page);
  await page.evaluate(() => {
    (window as unknown as EmulatorWindow).__headset.primaryInputMode = "controller";
  });

  // Acceptance 11: the same view-model checks as on the laptop, inside the session.
  await expect.poll(async () => (await hud(page)).panels.banner.rows[0]?.id, { timeout: 20_000 }).toBe("fan");
  const { panels } = await hud(page);
  expect(panels.banner.rows[0]).toMatchObject({ level: "warning", word: "WARNING", action: "DCU FAN to SEC, return to lander" });
  expect(panels.link).toMatchObject({ status: "ok", level: "nominal" });
  expect(panels.consumables.rows).toHaveLength(7);
  await sceneIsSteady(page);
  const seen = await view(page);
  expect(seen.panelsShown).toEqual(["banner", "consumables", "status", "switches", "vitals"]);
  expect(seen.panelsOutOfView, "every panel in view of both eyes").toEqual([]);
  await screenshot(page, testInfo, "warning-in-session");

  await pressButton(page, "a-button");
  await expect.poll(async () => (await hud(page)).input.last?.command).toEqual({
    type: "command",
    name: "ack_alert",
    args: { id: "fan" },
  });
  await expect
    .poll(async () => (await backend.state()).alerts.find((a) => a.id === "fan")?.acked, { timeout: 5000 })
    .toBe(true);
  await expect.poll(async () => (await hud(page)).panels.banner.rows.find((r) => r.id === "fan")?.acked).toBe(true);
  expect((await hud(page)).input.count, "one press, one intent").toBe(1);

  await pressButton(page, "b-button");
  await expect.poll(async () => (await hud(page)).panels.details.open, { timeout: 5000 }).toBe(true);
  await expect.poll(async () => (await view(page)).panelsShown).toEqual(["banner", "detailsLeft", "detailsRight", "status"]);
  await sceneIsSteady(page);
  const open = await view(page);
  expect(open.panelsOutOfView, "the details page in view of both eyes").toEqual([]);
  console.log(`draw calls, emulated headset: ${open.drawCalls} (details open), most ${open.maxDrawCalls}`);
  expect(open.maxDrawCalls).toBeLessThanOrEqual(100);
});
