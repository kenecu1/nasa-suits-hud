import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import {
  angleBox,
  CLEAR_ZONE,
  EYES,
  LAYOUT,
  overlaps,
  PANELS_DETAILS_CLOSED,
  PANELS_DETAILS_OPEN,
  reach,
  type PanelName,
} from "./layout";

const ALL = Object.keys(LAYOUT) as PanelName[];

describe("angleBox", () => {
  it("measures a centred panel symmetrically", () => {
    const box = angleBox({ yawDeg: 0, pitchDeg: 0, anchor: "center", widthPx: 2400, heightPx: 0 });
    expect(box.left).toBeCloseTo(45, 6); // a 1.2 m half-width at 1.2 m is 45 degrees
    expect(box.right).toBeCloseTo(-45, 6);
  });

  it("hangs a top-anchored panel below its anchor", () => {
    const box = angleBox({ yawDeg: 0, pitchDeg: 20, anchor: "top", widthPx: 0, heightPx: 1200 * Math.tan(Math.PI / 18) });
    expect(box.top).toBeCloseTo(20, 6);
    expect(box.bottom).toBeCloseTo(10, 6);
  });

  it("turns positive yaw to the left", () => {
    const box = angleBox({ yawDeg: 30, pitchDeg: 0, anchor: "center", widthPx: 10, heightPx: 10 });
    expect(box.left).toBeGreaterThan(30);
    expect(box.right).toBeLessThan(30);
    expect(box.right).toBeGreaterThan(29);
  });

  it("knows overlap from touching", () => {
    const a = { left: 10, right: 0, top: 10, bottom: 0 };
    expect(overlaps(a, { left: 5, right: -5, top: 5, bottom: -5 })).toBe(true);
    expect(overlaps(a, { left: 0, right: -5, top: 5, bottom: -5 })).toBe(false);
  });
});

describe("reach", () => {
  it("is 1 at the edge of a picture", () => {
    const eye = { name: "test", eyeX: 0, tanX: 1, tanY: 1 };
    // corners 45 degrees to either side at the panel distance
    const box = { yawDeg: 0, pitchDeg: 0, anchor: "center" as const, widthPx: 2400, heightPx: 0 };
    expect(reach(box, eye)).toBeCloseTo(1, 6);
  });

  it("is larger for the eye on the far side", () => {
    const box = LAYOUT.consumables; // to the right
    const left = EYES.find((e) => e.name === "left eye")!;
    const right = EYES.find((e) => e.name === "right eye")!;
    expect(reach(box, left)).toBeGreaterThan(reach(box, right));
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

  it.each(ALL.flatMap((name) => EYES.map((eye): [PanelName, string] => [name, eye.name])))(
    "%s fits inside the %s's picture",
    (name, eyeName) => {
      const eye = EYES.find((e) => e.name === eyeName)!;
      expect(reach(LAYOUT[name], eye)).toBeLessThanOrEqual(theme.view.edgeMargin);
    },
  );

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

  it("shows every panel in one of the two sets", () => {
    expect(new Set([...PANELS_DETAILS_CLOSED, ...PANELS_DETAILS_OPEN])).toEqual(new Set(ALL));
  });
});
