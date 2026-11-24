import { describe, expect, it } from "vitest";
import { dmmToPx, LEVELS, theme } from "../theme";
import { bannerVm } from "./banner.vm";
import { clockVm } from "./clock.vm";
import { consumablesVm } from "./consumables.vm";
import { detailsVm } from "./details.vm";
import { buildHud } from "./hud";
import { linkVm } from "./link.vm";
import { switchesVm } from "./switches.vm";
import { deepFreeze, makeAlert, makeState } from "./testState";
import { toneVm } from "./tone.vm";
import { vitalsVm } from "./vitals.vm";

describe("buildHud", () => {
  it("returns exactly the eight view models", () => {
    expect(Object.keys(buildHud(makeState(), "live")).sort()).toEqual([
      "banner",
      "clock",
      "consumables",
      "details",
      "link",
      "switches",
      "tone",
      "vitals",
    ]);
  });

  it.each(["live", "offline", "connecting"] as const)("puts each view model under its own key for conn %s", (conn) => {
    const state = makeState({ alerts: [makeAlert("o2_low")] });
    const prev = makeState();
    expect(buildHud(state, conn, prev)).toEqual({
      banner: bannerVm(state, conn),
      tone: toneVm(state, prev, conn),
      consumables: consumablesVm(state, conn),
      vitals: vitalsVm(state, conn),
      switches: switchesVm(state, conn),
      details: detailsVm(state, conn),
      clock: clockVm(state, conn),
      link: linkVm(state, conn),
    });
  });

  it("returns the eight panels without a state", () => {
    const hud = buildHud(null, "connecting");
    expect(Object.keys(hud)).toHaveLength(8);
    expect(hud).toEqual({
      banner: bannerVm(null, "connecting"),
      tone: toneVm(null, null, "connecting"),
      consumables: consumablesVm(null, "connecting"),
      vitals: vitalsVm(null, "connecting"),
      switches: switchesVm(null, "connecting"),
      details: detailsVm(null, "connecting"),
      clock: clockVm(null, "connecting"),
      link: linkVm(null, "connecting"),
    });
  });

  it("shows the words the wearer reads, live and offline", () => {
    const live = buildHud(makeState(), "live");
    expect(live.consumables.rows[0]).toMatchObject({ label: "O2 PRI", text: "92%", word: "NOMINAL", shape: "circle" });
    expect(live.switches.dcu.rows[1]).toMatchObject({ label: "OXY", text: "PRI", current: true });
    expect(live.clock.text).toBe("00:21:52");
    expect(live.link).toMatchObject({ label: "LINK", text: "TSS OK", mode: "SIM", status: "ok" });
    expect(live.banner.visible).toBe(false);

    const offline = buildHud(makeState(), "offline");
    expect(offline.consumables.rows[0]).toMatchObject({ text: "92%", word: "STALE", shape: "square" });
    expect(offline.switches.dcu.rows[1]).toMatchObject({ text: "PRI", current: false });
    expect(offline.link).toMatchObject({ text: "OFFLINE", word: "WARNING", shape: "triangle" });
  });

  it("passes the previous state to the tone only", () => {
    const state = makeState({ alerts: [makeAlert("o2_low")] });
    expect(buildHud(state, "live", makeState()).tone.play).toBe(true);
    expect(buildHud(state, "live", state).tone.play).toBe(false);
    expect(buildHud(state, "live").banner).toEqual(buildHud(state, "live", makeState()).banner);
  });

  it("does not mutate its input", () => {
    const state = deepFreeze(makeState({ alerts: [makeAlert("a"), makeAlert("b", "caution")] }));
    const prev = deepFreeze(makeState());
    for (const conn of ["live", "offline", "connecting"] as const) {
      expect(() => buildHud(state, conn, prev)).not.toThrow();
    }
    expect(state).toEqual(makeState({ alerts: [makeAlert("a"), makeAlert("b", "caution")] }));
  });

  it("gives the same result when called twice with the same input", () => {
    const state = makeState({ alerts: [makeAlert("a")] });
    expect(buildHud(state, "live", null)).toEqual(buildHud(state, "live", null));
  });
});

describe("theme.level", () => {
  const styles = LEVELS.map((level) => theme.level[level]);

  it("has a style for exactly the six levels of the contract, including off", () => {
    expect(Object.keys(theme.level).sort()).toEqual(["caution", "nominal", "off", "stale", "unknown", "warning"]);
    expect([...LEVELS].sort()).toEqual(Object.keys(theme.level).sort());
  });

  it("gives off the dash shape and the word OFF", () => {
    expect(theme.level.off).toMatchObject({ shape: "dash", word: "OFF" });
  });

  it("gives every level its own shape", () => {
    expect(new Set(styles.map((s) => s.shape)).size).toBe(6);
  });

  it("gives every level its own word", () => {
    expect(new Set(styles.map((s) => s.word)).size).toBe(6);
  });

  it("gives every level its own colour", () => {
    expect(new Set(styles.map((s) => s.color)).size).toBe(6);
  });
});

describe("theme font sizes (acceptance 6)", () => {
  it("keeps every text size at or above theme.minDmm", () => {
    for (const [name, dmm] of Object.entries(theme.fontDmm)) {
      expect(dmm, name).toBeGreaterThanOrEqual(theme.minDmm);
    }
  });

  it("has theme.font as theme.fontDmm converted by dmmToPx", () => {
    expect(Object.keys(theme.font).sort()).toEqual(Object.keys(theme.fontDmm).sort());
    for (const [name, dmm] of Object.entries(theme.fontDmm)) {
      expect(theme.font[name as keyof typeof theme.font], name).toBeCloseTo(dmmToPx(dmm), 10);
    }
  });

  it("converts dmm to panel pixels at the panel distance (24 dmm at 1.2 m is 28.8 px)", () => {
    expect(dmmToPx(24)).toBeCloseTo(28.8, 10);
    expect(dmmToPx(0)).toBe(0);
  });
});
