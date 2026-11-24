import { describe, expect, it } from "vitest";
import { LEVELS, theme } from "../theme";
import { composite, contrastRatio, luminance, parseHex } from "./contrast";

const WHITE = "#ffffff";
const backing = composite(theme.color.panel, theme.panel.opacity, WHITE);

describe("contrast maths", () => {
  it("gives 21:1 for white on black and 1:1 for a colour on itself", () => {
    expect(contrastRatio(parseHex("#ffffff"), parseHex("#000000"))).toBeCloseTo(21, 5);
    expect(contrastRatio(parseHex("#7ee8a8"), parseHex("#7ee8a8"))).toBeCloseTo(1, 9);
  });

  it("matches a known WCAG value (#777777 on white is about 4.48:1)", () => {
    expect(contrastRatio(parseHex("#777777"), parseHex(WHITE))).toBeCloseTo(4.48, 2);
  });

  it("mixes the backing with what is behind it", () => {
    expect(composite("#000000", 0.5, WHITE)).toEqual([127.5, 127.5, 127.5]);
    expect(composite("#0b1118", 1, WHITE)).toEqual([11, 17, 24]);
  });

  it("refuses a colour that is not #rrggbb", () => {
    expect(() => parseHex("red")).toThrow(/not a #rrggbb/);
    expect(() => parseHex("#fff")).toThrow(/not a #rrggbb/);
  });
});

describe("acceptance 6: text on the panel backing, composited over white at the panel opacity", () => {
  it("uses opacity 0.92 (decision F)", () => {
    expect(theme.panel.opacity).toBe(0.92);
  });

  it("is lighter than the raw panel colour, so the check is the worst case and not the easy one", () => {
    expect(luminance(backing)).toBeGreaterThan(luminance(parseHex(theme.color.panel)));
  });

  const texts: [string, string][] = [
    ["text", theme.color.text],
    ["label", theme.color.label],
    ...LEVELS.map((level): [string, string] => [`level ${level}`, theme.level[level].color]),
  ];

  it.each(texts)("%s has at least 7:1", (_name, colour) => {
    expect(contrastRatio(parseHex(colour), backing)).toBeGreaterThanOrEqual(7);
  });

  it("keeps the dimmed off colour dimmer than the unknown colour it sits beside", () => {
    expect(luminance(parseHex(theme.level.off.color))).toBeLessThan(luminance(parseHex(theme.level.unknown.color)));
  });
});
