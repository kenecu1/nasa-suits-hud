// Guards for project rules that the type checker cannot see (CLAUDE.md, "Rules that protect
// the design"), and for the data file the client reads.
import { describe, expect, it } from "vitest";
import ranges from "../../../data/ranges.json";

const SOURCES = import.meta.glob<string>("../scene/*.tsx", { query: "?raw", import: "default", eager: true });
const COMPONENTS = Object.entries(SOURCES).map(([path, source]): [string, string] => [path.replace("../scene/", ""), source]);

describe("components take sizes and colours from theme.ts", () => {
  it("finds the components", () => {
    expect(COMPONENTS.length).toBeGreaterThan(5);
  });

  it.each(COMPONENTS)("%s has no literal font size", (_file, source) => {
    expect(source).not.toMatch(/fontSize=\{?\s*["']?\d/);
  });

  it.each(COMPONENTS)("%s has no literal colour", (_file, source) => {
    // LevelShape's SVG drawings carry geometry only; their colour comes in as a prop.
    expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/);
  });

  it.each(COMPONENTS)("%s listens to no key or button (input/ does)", (_file, source) => {
    expect(source).not.toMatch(/keydown|keyup|onKey|gamepad|inputSources/);
  });
});

describe("data/ranges.json, as the client reads it", () => {
  it.each(Object.entries(ranges.ranges))("%s has a numeric min below max and a known check", (_name, entry) => {
    const e = entry as { min: unknown; max: unknown; check: unknown };
    expect(typeof e.min).toBe("number");
    expect(typeof e.max).toBe("number");
    expect(e.min as number).toBeLessThan(e.max as number);
    expect(["low", "high", "both"]).toContain(e.check);
  });
});
