import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import {
  angleBox,
  CLEAR_ZONE,
  inside,
  LAYOUT,
  overlaps,
  PANELS_DETAILS_CLOSED,
  PANELS_DETAILS_OPEN,
  VIEW_LIMIT,
  type PanelName,
} from "./layout";

const ALL = Object.keys(LAYOUT) as PanelName[];

describe("angleBox", () => {
  it("measures a centred panel symmetrically", () => {
    const box = angleBox({ yawDeg: 0, pitchDeg: 0, anchor: "center", widthPx: 2400, heightPx: 2400 });
    expect(box.left).toBeCloseTo(45, 6); // 1.2 m half-width at 1.2 m is 45 degrees
    expect(box.right).toBeCloseTo(-45, 6);
    expect(box.top).toBeCloseTo(45, 6);
  });

  it("hangs a top-anchored panel below its anchor", () => {
    const box = angleBox({ yawDeg: 0, pitchDeg: 20, anchor: "top", widthPx: 100, heightPx: 1200 * Math.tan(Math.PI / 18) });
    expect(box.top).toBe(20);
    expect(box.bottom).toBeCloseTo(10, 6);
  });

  it("knows overlap from touching", () => {
    const a = { left: 10, right: 0, top: 10, bottom: 0 };
    expect(overlaps(a, { left: 5, right: -5, top: 5, bottom: -5 })).toBe(true);
    expect(overlaps(a, { left: 0, right: -5, top: 5, bottom: -5 })).toBe(false);
  });
});

describe("acceptance 8: the centre of view stays clear", () => {
  it("is 30 degrees wide and 20 tall", () => {
    expect(CLEAR_ZONE.left - CLEAR_ZONE.right).toBe(30);
    expect(CLEAR_ZONE.top - CLEAR_ZONE.bottom).toBe(20);
  });

  it.each(ALL)("%s does not overlap the central 30 x 20 degrees", (name) => {
    expect(overlaps(angleBox(LAYOUT[name]), CLEAR_ZONE)).toBe(false);
  });

  it.each(ALL)("%s fits where the laptop camera and a headset eye can see it", (name) => {
    expect(inside(angleBox(LAYOUT[name]), VIEW_LIMIT)).toBe(true);
  });

  it.each([
    ["details closed", PANELS_DETAILS_CLOSED],
    ["details open", PANELS_DETAILS_OPEN],
  ] as const)("no two panels overlap with the %s", (_name, panels) => {
    for (const a of panels) {
      for (const b of panels) {
        if (a < b) expect(overlaps(angleBox(LAYOUT[a]), angleBox(LAYOUT[b])), `${a} and ${b}`).toBe(false);
      }
    }
  });

  it("keeps the laptop camera's view inside the limit it is checked against", () => {
    expect(theme.camera.fovDeg / 2).toBeGreaterThanOrEqual(theme.view.maxPitchDeg);
  });

  it("shows every panel in one of the two sets", () => {
    expect(new Set([...PANELS_DETAILS_CLOSED, ...PANELS_DETAILS_OPEN])).toEqual(new Set(ALL));
  });
});
