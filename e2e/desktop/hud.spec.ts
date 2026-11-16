// The laptop page against the real backend in sim mode (acceptance 13 and 15).
import { REAL_RECORDING } from "../support/backend";
import { expect, hud, hudIsLive, PAGE, sceneIsSteady, screenshot, test, view } from "../support/fixtures";

test("the panel shows the backend's oxygen value, switch position and link", async ({ page, backend }, testInfo) => {
  await page.goto(PAGE);
  await hudIsLive(page);

  const state = await backend.state();
  const oxygen = state.suit.values.oxy_pri_storage;
  expect(oxygen?.value, "the sim sends a primary oxygen value").toEqual(expect.any(Number));

  const { panels } = await hud(page);
  expect(panels.o2.text).toBe(`${Math.floor(oxygen!.value!)}%`);
  expect(panels.o2.level).toBe(oxygen!.level);
  expect(panels.o2.level).toBe("nominal");
  expect(panels.o2.word).toBe("NOMINAL");
  expect(panels.dcu.text).toBe(state.dcu!.oxy);
  expect(panels.dcu.current).toBe(true);
  expect(panels.link).toMatchObject({ status: "ok", text: "TSS OK", mode: "SIM", level: "nominal" });

  const seen = await view(page);
  expect(seen.presenting).toBe(false);
  expect(seen.panelInView).toBe(true);

  await screenshot(page, testInfo, "live");
});

test("a stopped backend shows offline within 4 s, and the page recovers without a reload", async ({
  page,
  backend,
}, testInfo) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  const before = await hud(page);
  expect(before.panels.o2.level).toBe("nominal");
  await page.evaluate(() => {
    (window as unknown as { __sameDocument: boolean }).__sameDocument = true;
  });

  await backend.stop();
  await expect.poll(async () => (await hud(page)).panels.link.status, { timeout: 4000 }).toBe("offline");

  // Nothing on screen may still look fresh: the last number stays, but as stale.
  const offline = (await hud(page)).panels;
  expect(offline.link).toMatchObject({ text: "OFFLINE", level: "warning" });
  expect(offline.o2).toMatchObject({ text: before.panels.o2.text, level: "stale", word: "STALE" });
  expect(offline.o2.color).not.toBe(before.panels.o2.color);
  expect(offline.dcu.current).toBe(false);
  await sceneIsSteady(page);
  await screenshot(page, testInfo, "offline");

  await backend.start();
  await expect.poll(async () => (await hud(page)).panels.link.status, { timeout: 20_000 }).toBe("ok");
  const after = (await hud(page)).panels;
  expect(after.o2).toMatchObject({ text: before.panels.o2.text, level: "nominal" });
  expect(after.dcu.current).toBe(true);
  expect(
    await page.evaluate(() => (window as unknown as { __sameDocument?: boolean }).__sameDocument),
    "the page must not have reloaded",
  ).toBe(true);
});

test("a value that is not the sim's reaches the page: replay of the real TSS recording", async ({ page, backend }) => {
  // The sim always says 92%. The recording of the real TSS drains from about 90%, so this
  // proves the page shows what the backend sends and not a number that happens to match.
  await backend.start({ mode: "replay", recording: REAL_RECORDING });
  await page.goto(PAGE);
  await expect.poll(async () => (await hud(page)).panels.link.mode, { timeout: 15_000 }).toBe("REPLAY");

  // The value moves, so read the backend and the page at the same moment and try again if a
  // new state landed in between.
  let shown = "";
  await expect
    .poll(
      async () => {
        const [state, onPage] = await Promise.all([backend.state(), hud(page)]);
        const value = state.suit.values.oxy_pri_storage?.value;
        shown = onPage.panels.o2.text;
        return typeof value === "number" && shown === `${Math.floor(value)}%`;
      },
      { timeout: 20_000 },
    )
    .toBe(true);
  expect(shown).toMatch(/^\d+%$/);
  expect(shown).not.toBe("92%");
  expect((await hud(page)).panels.dcu.text).toMatch(/^(PRI|SEC)$/);
});

test("the scene uses at most 50 draw calls", async ({ page, backend: _backend }) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  const seen = await view(page);
  console.log(`draw calls, laptop view: ${seen.maxDrawCalls}`);
  expect(seen.maxDrawCalls).toBeGreaterThan(0);
  expect(seen.maxDrawCalls).toBeLessThanOrEqual(50);
});
