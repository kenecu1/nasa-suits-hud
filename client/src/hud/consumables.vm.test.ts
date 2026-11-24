import { describe, expect, it } from "vitest";
import type { Level } from "../contract.gen";
import { theme } from "../theme";
import { CONSUMABLES, consumablesVm } from "./consumables.vm";
import { deepFreeze, makeState, makeValue, withValue } from "./testState";
import type { Conn } from "./types";

const NAMES = [
  "oxy_pri_storage",
  "oxy_sec_storage",
  "primary_battery_level",
  "secondary_battery_level",
  "scrubber_a_co2_storage",
  "scrubber_b_co2_storage",
  "coolant_storage",
];

const row = (vm: ReturnType<typeof consumablesVm>, name: string) => {
  const found = vm.rows.find((r) => r.name === name);
  if (found === undefined) throw new Error(`no row for ${name}`);
  return found;
};

describe("consumablesVm", () => {
  it("has the label CONSUMABLES", () => {
    expect(consumablesVm(makeState(), "live").label).toBe("CONSUMABLES");
  });

  it("has exactly the seven consumables, in CONSUMABLES order", () => {
    expect(CONSUMABLES).toEqual(NAMES);
    expect(consumablesVm(makeState(), "live").rows.map((r) => r.name)).toEqual(NAMES);
  });

  it("has the seven rows even without a state", () => {
    expect(consumablesVm(null, "connecting").rows.map((r) => r.name)).toEqual(NAMES);
  });

  it("writes labels and text of the values", () => {
    const vm = consumablesVm(makeState(), "live");
    expect(row(vm, "oxy_pri_storage")).toMatchObject({ label: "O2 PRI", text: "92%" });
    expect(row(vm, "coolant_storage")).toMatchObject({ label: "COOLANT", text: "95%" });
  });

  it.each<[number, number]>([
    [0, 0],
    [50, 0.5],
    [92, 0.92],
    [100, 1],
    [100.5, 1],
    [250, 1],
    [-5, 0],
    [-0.0001, 0],
  ])("fills a bar with the value %s to %s", (value, fill) => {
    const state = withValue("oxy_pri_storage", makeValue(value, "nominal", "%"));
    expect(row(consumablesVm(state, "live"), "oxy_pri_storage").fill).toBeCloseTo(fill, 10);
  });

  it("puts the warning limit mark at min/100 for a value checked low", () => {
    const vm = consumablesVm(makeState(), "live");
    expect(row(vm, "oxy_pri_storage").limit).toBeCloseTo(0.2, 10);
    expect(row(vm, "primary_battery_level").limit).toBeCloseTo(0.2, 10);
    expect(row(vm, "coolant_storage").limit).toBeCloseTo(0.8, 10);
  });

  it("puts the warning limit mark at max/100 for a value checked high", () => {
    const vm = consumablesVm(makeState(), "live");
    expect(row(vm, "scrubber_a_co2_storage").limit).toBeCloseTo(0.6, 10);
    expect(row(vm, "scrubber_b_co2_storage").limit).toBeCloseTo(0.6, 10);
  });

  it("gives every row a limit between 0 and 1", () => {
    for (const r of consumablesVm(makeState(), "live").rows) {
      expect(r.limit).not.toBeNull();
      expect(r.limit).toBeGreaterThanOrEqual(0);
      expect(r.limit).toBeLessThanOrEqual(1);
    }
  });

  it("keeps the limit when the value is unknown", () => {
    const state = withValue("oxy_pri_storage", makeValue(null, "unknown", "%"));
    expect(row(consumablesVm(state, "live"), "oxy_pri_storage").limit).toBeCloseTo(0.2, 10);
  });

  it("shows an empty bar, -- and the unknown look for a value without a number", () => {
    const state = withValue("oxy_pri_storage", makeValue(null, "unknown", "%"));
    expect(row(consumablesVm(state, "live"), "oxy_pri_storage")).toMatchObject({
      fill: 0,
      text: "--",
      level: "unknown",
      ...theme.level.unknown,
    });
  });

  it("shows an empty bar and -- for a value that is missing, NaN or Infinity", () => {
    const missing = withValue("oxy_pri_storage", undefined);
    const nan = withValue("oxy_pri_storage", makeValue(Number.NaN, "nominal", "%"));
    const inf = withValue("oxy_pri_storage", makeValue(Number.POSITIVE_INFINITY, "nominal", "%"));
    for (const state of [missing, nan, inf]) {
      expect(row(consumablesVm(state, "live"), "oxy_pri_storage")).toMatchObject({ fill: 0, text: "--", level: "unknown" });
    }
  });

  it("shows -- and an empty bar for every row without a state", () => {
    for (const r of consumablesVm(null, "connecting").rows) expect(r).toMatchObject({ fill: 0, text: "--", level: "unknown" });
  });

  it.each<Level>(["nominal", "caution", "warning", "stale"])("takes the level %s from the backend", (level) => {
    const state = withValue("oxy_sec_storage", makeValue(30, level, "%"));
    expect(row(consumablesVm(state, "live"), "oxy_sec_storage")).toMatchObject({ level, ...theme.level[level] });
  });

  it("does not decide levels itself: a value below its limit stays nominal if the backend says so", () => {
    const state = withValue("oxy_pri_storage", makeValue(5, "nominal", "%"));
    expect(row(consumablesVm(state, "live"), "oxy_pri_storage").level).toBe("nominal");
  });

  it("floors a value checked low and rounds one checked high up in the text", () => {
    const state = withValue("scrubber_a_co2_storage", makeValue(60.2, "warning", "%"), withValue("oxy_pri_storage", makeValue(19.6, "warning", "%")));
    const vm = consumablesVm(state, "live");
    expect(row(vm, "oxy_pri_storage").text).toBe("19%");
    expect(row(vm, "scrubber_a_co2_storage").text).toBe("61%");
  });

  it.each<Conn>(["offline", "connecting"])("draws every row stale and keeps bar and text when conn is %s", (conn) => {
    const vm = consumablesVm(makeState(), conn);
    for (const r of vm.rows) expect(r).toMatchObject({ level: "stale", ...theme.level.stale });
    expect(row(vm, "oxy_pri_storage")).toMatchObject({ text: "92%", fill: 0.92 });
  });

  it("does not change its input", () => {
    expect(() => consumablesVm(deepFreeze(makeState()), "live")).not.toThrow();
  });
});

describe("consumablesVm, unknown and off rows", () => {
  it.each(["scrubber_b_co2_storage", "coolant_storage"])("shows -- with an empty bar and the unknown look when %s has no number", (name) => {
    const row = consumablesVm(withValue(name, makeValue(null, "unknown", "%")), "live").rows.find((r) => r.name === name);
    expect(row).toMatchObject({ text: "--", fill: 0, level: "unknown", word: "NO DATA", wordText: "NO DATA" });
  });

  it("shows -- for a level word this client does not know, never a bare number", () => {
    const odd = { value: 50, unit: "%", level: "critical" } as unknown as ReturnType<typeof makeValue>;
    const row = consumablesVm(withValue("coolant_storage", odd), "live").rows.find((r) => r.name === "coolant_storage");
    expect(row).toMatchObject({ text: "--", fill: 0, level: "unknown" });
  });

  it("draws an off row with its number, the dash and the word OFF", () => {
    const row = consumablesVm(withValue("scrubber_a_co2_storage", makeValue(0, "off", "%")), "live").rows[4];
    expect(row).toMatchObject({ name: "scrubber_a_co2_storage", text: "0%", level: "off", shape: "dash", wordText: "OFF" });
  });
});

