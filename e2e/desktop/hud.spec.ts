// The laptop page against the real backend in sim mode. M1 acceptance 13 and 15, and M2
// acceptance 9 (screenshots), 10 (keyboard: details page and ack_alert) and 12 (draw calls).
import { REAL_RECORDING } from "../support/backend";
import { expect, hud, hudIsLive, PAGE, sceneIsSteady, screenshot, test, view, type Page } from "../support/fixtures";

const CLOSED = ["banner", "consumables", "status", "switches", "vitals"];
const CLOSED_NO_ALERTS = CLOSED.filter((p) => p !== "banner");

/** Wait until the banner's top row is this alert, as the page shows it. */
async function topAlertIs(page: Page, id: string, timeout = 20_000): Promise<void> {
  await expect.poll(async () => (await hud(page)).panels.banner.rows[0]?.id, { timeout }).toBe(id);
  await sceneIsSteady(page);
}

test("nominal: every panel shows the backend's values, out of the centre of view", async ({ page, backend }, testInfo) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  const state = await backend.state();
  const oxygen = state.suit.values.oxy_pri_storage;
  expect(oxygen?.value, "the sim sends a primary oxygen value").toEqual(expect.any(Number));

  const { panels } = await hud(page);
  const o2 = panels.consumables.rows.find((r) => r.name === "oxy_pri_storage");
  expect(o2).toMatchObject({ text: `${Math.floor(oxygen!.value!)}%`, level: "nominal", shape: "circle" });
  expect(panels.consumables.rows.map((r) => r.level)).toEqual(Array(7).fill("nominal"));
  expect(panels.switches.dcu.rows.find((r) => r.label === "OXY")).toMatchObject({ text: state.dcu!.oxy, current: true });
  expect(panels.link).toMatchObject({ status: "ok", text: "TSS OK", mode: "SIM", level: "nominal" });
  expect(panels.clock.text).toMatch(/^\d\d:\d\d:\d\d$/);
  expect(panels.banner.visible).toBe(false);
  expect(panels.details.open).toBe(false);

  const seen = await view(page);
  expect(seen.presenting).toBe(false);
  expect(seen.panelsShown).toEqual(CLOSED_NO_ALERTS);
  expect(seen.panelsOutOfView).toEqual([]);
  await screenshot(page, testInfo, "nominal");
});

test("the inactive fan shows as OFF, not as a warning", async ({ page, backend }) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  const state = await backend.state();
  const inactive = state.dcu!.fan === "PRI" ? "fan_sec_rpm" : "fan_pri_rpm";
  expect(state.suit.values[inactive]?.level).toBe("off");
  await page.keyboard.press("KeyD");
  await expect.poll(async () => (await hud(page)).panels.details.open, { timeout: 5000 }).toBe(true);
  const row = (await hud(page)).panels.details.columns[1].flatMap((g) => g.rows).find((r) => r.name === inactive);
  expect(row).toMatchObject({ level: "off", word: "OFF", shape: "dash" });
});

test("caution: a high heart rate raises a caution with its action, and the vital grows", async ({ page, backend }, testInfo) => {
  await backend.start({ mode: "sim", scenario: "heart_rate_high", speed: 4 });
  await page.goto(PAGE);
  await hudIsLive(page);
  await topAlertIs(page, "heart_rate");
  const { panels } = await hud(page);
  expect(panels.banner.rows[0]).toMatchObject({ level: "caution", word: "CAUTION", shape: "diamond", action: "Slow down" });
  expect(panels.vitals.rows.find((r) => r.name === "heart_rate")).toMatchObject({ level: "caution", grown: true });
  expect((await hud(page)).tones, "a caution plays no tone").toBe(0);
  await screenshot(page, testInfo, "caution");
});

test("warning: a fan failure raises a warning with a tone, and key A acknowledges the alert shown on top", async ({
  page,
  backend,
}, testInfo) => {
  // The page is watching when the warning arrives: the tone is for a new warning, not for one
  // that was already there when the page loaded.
  await page.goto(PAGE);
  await hudIsLive(page);
  expect((await hud(page)).tones).toBe(0);
  await page.keyboard.press("KeyQ"); // any key: browsers allow sound only after one
  await backend.start({ mode: "sim", scenario: "fan_failure", speed: 10 });
  await topAlertIs(page, "fan");
  const before = await hud(page);
  expect(before.panels.banner.rows[0]).toMatchObject({
    level: "warning",
    word: "WARNING",
    shape: "triangle",
    action: "DCU FAN to SEC, return to lander",
    acked: false,
  });
  expect(before.panels.banner.topId).toBe("fan");
  expect(before.tones, "a new warning plays the tone once").toBe(1);
  expect(before.tonesMissed).toBe(0);
  await screenshot(page, testInfo, "warning");

  await page.keyboard.press("KeyA");
  // The command named the alert the banner showed (decision B) ...
  await expect.poll(async () => (await hud(page)).input.last?.command).toEqual({
    type: "command",
    name: "ack_alert",
    args: { id: "fan" },
  });
  expect((await hud(page)).input.last?.sent).toBe(true);
  // ... the backend holds it as acknowledged, and the page shows what the backend says.
  await expect
    .poll(async () => (await backend.state()).alerts.find((a) => a.id === "fan")?.acked, { timeout: 5000 })
    .toBe(true);
  await expect.poll(async () => (await hud(page)).panels.banner.rows.find((r) => r.id === "fan")?.acked).toBe(true);
  expect((await hud(page)).tones, "acknowledging plays nothing").toBe(1);
});

test("decision B: after the fan is acknowledged, a new oxygen warning goes on top with a tone, and A acknowledges it, not the fan", async ({
  page,
  backend,
}) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  await page.keyboard.press("KeyQ"); // any key: lets the page play sound
  await backend.start({ mode: "sim", scenario: "fan_then_oxygen" });
  await topAlertIs(page, "fan");
  expect((await hud(page)).tones).toBe(1);
  await page.keyboard.press("KeyA");
  await expect.poll(async () => (await hud(page)).panels.banner.rows.find((r) => r.id === "fan")?.acked).toBe(true);

  // The oxygen warning arrives: unacknowledged goes first, the fan sinks but stays listed.
  await topAlertIs(page, "oxygen", 30_000);
  const panels = (await hud(page)).panels;
  expect(panels.banner.rows.map((r) => [r.id, r.acked])).toEqual([
    ["oxygen", false],
    ["fan", true],
  ]);
  expect(panels.banner.rows[0]?.action).toBe("DCU OXY to SEC, return to lander");
  expect((await hud(page)).tones, "a new warning plays the tone again").toBe(2);

  await page.keyboard.press("KeyA");
  await expect.poll(async () => (await hud(page)).input.last?.command.args.id).toBe("oxygen");
  await expect
    .poll(async () => (await backend.state()).alerts.map((a) => [a.id, a.acked]), { timeout: 5000 })
    .toEqual([
      ["oxygen", true],
      ["fan", true],
    ]);
  expect((await hud(page)).tones).toBe(2);
});

test("link lost: one link alert, every value stale, no suit alerts", async ({ page, backend }, testInfo) => {
  await backend.start({ mode: "sim", scenario: "link_loss" });
  await page.goto(PAGE);
  await hudIsLive(page);
  await expect
    .poll(async () => (await hud(page)).panels.link.status, { timeout: 15_000 })
    .toBe("unreachable");
  await expect.poll(async () => (await hud(page)).panels.banner.rows.length).toBe(1);
  const { panels } = await hud(page);
  expect(panels.link.level).toBe("warning");
  expect(panels.banner.rows[0]?.level).toBe("warning");
  expect(panels.consumables.rows.map((r) => r.level)).toEqual(Array(7).fill("stale"));
  expect(panels.vitals.rows.map((r) => r.level)).toEqual(["stale", "stale"]);
  await sceneIsSteady(page);
  await screenshot(page, testInfo, "link-lost");
});

test("EVA not started: values show, no suit alerts", async ({ page, backend }, testInfo) => {
  await backend.start({ mode: "sim", scenario: "eva_not_started" });
  await page.goto(PAGE);
  await hudIsLive(page);
  await expect.poll(async () => (await hud(page)).panels.clock.text, { timeout: 15_000 }).toBe("NOT STARTED");
  const { panels } = await hud(page);
  expect(panels.banner.visible).toBe(false);
  expect(panels.consumables.rows.find((r) => r.name === "oxy_pri_storage")?.text).toMatch(/^\d+%$/);
  await sceneIsSteady(page);
  await screenshot(page, testInfo, "eva-not-started");
});

test("key D opens a details page that lists every telemetry name in the contract, and closes it", async ({
  page,
  backend,
}, testInfo) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  await page.keyboard.press("KeyD");
  await expect.poll(async () => (await hud(page)).panels.details.open, { timeout: 5000 }).toBe(true);
  expect((await backend.state()).ui.details_open, "the backend holds the page open").toBe(true);

  const names = Object.keys((await backend.state()).suit.values).sort();
  expect(names).toHaveLength(23);
  expect([...(await hud(page)).panels.details.names].sort()).toEqual(names);

  await sceneIsSteady(page);
  const seen = await view(page);
  expect(seen.panelsShown).toEqual(["detailsLeft", "detailsRight", "status"]);
  expect(seen.panelsOutOfView).toEqual([]);
  await screenshot(page, testInfo, "details");

  await page.keyboard.press("KeyD");
  await expect.poll(async () => (await hud(page)).panels.details.open, { timeout: 5000 }).toBe(false);
  await expect.poll(async () => (await view(page)).panelsShown).toEqual(CLOSED_NO_ALERTS);
});

test("at most 100 draw calls with every panel shown, details closed and open, with alerts", async ({ page, backend }) => {
  await backend.start({ mode: "sim", scenario: "fan_failure", speed: 10 });
  await page.goto(PAGE);
  await hudIsLive(page);
  await topAlertIs(page, "fan");
  expect((await view(page)).panelsShown).toEqual(CLOSED);
  const closed = (await view(page)).drawCalls;
  await page.keyboard.press("KeyD");
  await expect.poll(async () => (await view(page)).panelsShown, { timeout: 5000 }).toEqual([
    "banner",
    "detailsLeft",
    "detailsRight",
    "status",
  ]);
  await sceneIsSteady(page);
  const seen = await view(page);
  console.log(`draw calls, laptop view: ${closed} (details closed), ${seen.drawCalls} (open), most ${seen.maxDrawCalls}`);
  expect(seen.maxDrawCalls).toBeGreaterThan(0);
  expect(seen.maxDrawCalls).toBeLessThanOrEqual(100);
});

test("a stopped backend shows offline within 4 s, and the page recovers without a reload", async ({
  page,
  backend,
}, testInfo) => {
  await page.goto(PAGE);
  await hudIsLive(page);
  const o2 = async () => (await hud(page)).panels.consumables.rows.find((r) => r.name === "oxy_pri_storage");
  const before = await o2();
  expect(before?.level).toBe("nominal");
  await page.evaluate(() => {
    (window as unknown as { __sameDocument: boolean }).__sameDocument = true;
  });

  await backend.stop();
  await expect.poll(async () => (await hud(page)).panels.link.status, { timeout: 4000 }).toBe("offline");
  // Nothing on screen may still look fresh: the last number stays, but as stale.
  const offline = (await hud(page)).panels;
  expect(offline.link).toMatchObject({ text: "OFFLINE", level: "warning" });
  expect(await o2()).toMatchObject({ text: before?.text, level: "stale", word: "STALE" });
  expect((await o2())?.color).not.toBe(before?.color);
  expect(offline.switches.dcu.rows.every((r) => !r.current)).toBe(true);
  // A key press while offline is dropped with a trace, not queued.
  await page.keyboard.press("KeyA");
  await expect.poll(async () => (await hud(page)).input.dropped).toBe(1);
  await sceneIsSteady(page);
  await screenshot(page, testInfo, "offline");

  await backend.start();
  await expect.poll(async () => (await hud(page)).panels.link.status, { timeout: 20_000 }).toBe("ok");
  expect(await o2()).toMatchObject({ text: before?.text, level: "nominal" });
  expect((await hud(page)).panels.switches.dcu.rows.every((r) => r.current)).toBe(true);
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
        shown = onPage.panels.consumables.rows.find((r) => r.name === "oxy_pri_storage")?.text ?? "";
        return typeof value === "number" && shown === `${Math.floor(value)}%`;
      },
      { timeout: 20_000 },
    )
    .toBe(true);
  expect(shown).toMatch(/^\d+%$/);
  expect(shown).not.toBe("92%");
  expect((await hud(page)).panels.switches.dcu.rows.find((r) => r.label === "OXY")?.text).toMatch(/^(PRI|SEC)$/);
});
