import { describe, expect, it } from "vitest";
import type { Level } from "../contract.gen";
import { theme } from "../theme";
import { deepFreeze, makeState, makeValue, withValue } from "./testState";
import type { Conn } from "./types";
import { VITALS, vitalsVm } from "./vitals.vm";

describe("vitalsVm", () => {
  it("has the label VITALS and the rows heart_rate and temperature, in that order", () => {
    const vm = vitalsVm(makeState(), "live");
    expect(VITALS).toEqual(["heart_rate", "temperature"]);
    expect(vm.label).toBe("VITALS");
    expect(vm.rows.map((r) => r.name)).toEqual(["heart_rate", "temperature"]);
  });

  it("writes labels and text", () => {
    const vm = vitalsVm(makeState(), "live");
    expect(vm.rows[0]).toMatchObject({ label: "HEART", text: "90 bpm" });
    expect(vm.rows[1]).toMatchObject({ label: "TEMP", text: "21.5 °C" });
  });

  it("keeps both rows without a state, showing -- and the unknown look", () => {
    const vm = vitalsVm(null, "connecting");
    expect(vm.rows).toHaveLength(2);
    for (const r of vm.rows) expect(r).toMatchObject({ text: "--", level: "unknown", grown: false, ...theme.level.unknown });
  });

  it.each<[Level, boolean]>([
    ["nominal", false],
    ["caution", true],
    ["warning", true],
    ["unknown", false],
    ["stale", false],
    ["off", false],
  ])("level %s from the backend: grown is %s", (level, grown) => {
    const state = withValue("heart_rate", makeValue(90, level, "bpm"));
    expect(vitalsVm(state, "live").rows[0]?.grown).toBe(grown);
  });

  it("grows only the row that is off-nominal", () => {
    const state = withValue("temperature", makeValue(31, "caution", "°C"));
    expect(vitalsVm(state, "live").rows.map((r) => r.grown)).toEqual([false, true]);
  });

  it("does not grow a value with no number even if the backend sent a warning level", () => {
    const state = withValue("heart_rate", makeValue(null, "warning", "bpm"));
    expect(vitalsVm(state, "live").rows[0]).toMatchObject({ grown: false, level: "unknown", text: "--" });
  });

  it.each<Conn>(["offline", "connecting"])("does not grow a warning value when conn is %s (it is stale)", (conn) => {
    const state = withValue("heart_rate", makeValue(170, "warning", "bpm"));
    expect(vitalsVm(state, conn).rows[0]).toMatchObject({ grown: false, level: "stale", text: "170 bpm", ...theme.level.stale });
  });

  it("does not change its input", () => {
    expect(() => vitalsVm(deepFreeze(makeState()), "live")).not.toThrow();
  });
});
