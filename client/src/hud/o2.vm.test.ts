import { describe, expect, it } from "vitest";
import type { Level, State, SuitValue } from "../contract.gen";
import { theme } from "../theme";
import { o2Vm } from "./o2.vm";

function makeState(oxy: SuitValue = { value: 92, unit: "%", level: "nominal" }): State {
  return {
    type: "state",
    v: 2,
    seq: 1,
    t: 100,
    link: { tss: "ok", age_s: 0.2, mode: "sim" },
    eva: { started: false, elapsed_s: 0, phase: null },
    suit: { values: { oxy_pri_storage: oxy }, faults: null },
    dcu: { batt: "LOCAL", oxy: "PRI", comm: "A", fan: "PRI", pump: "OPEN", co2: "A" },
    uia: null,
  };
}

function deepFreeze<T>(obj: T): T {
  if (obj !== null && typeof obj === "object") {
    Object.values(obj).forEach((child) => deepFreeze(child));
    Object.freeze(obj);
  }
  return obj;
}

describe("o2Vm", () => {
  it("labels the panel O2 PRI", () => {
    expect(o2Vm(makeState(), "live").label).toBe("O2 PRI");
  });

  it.each<[string, SuitValue, string, Level]>([
    ["nominal", { value: 92, unit: "%", level: "nominal" }, "92%", "nominal"],
    ["caution", { value: 22, unit: "%", level: "caution" }, "22%", "caution"],
    ["warning", { value: 15, unit: "%", level: "warning" }, "15%", "warning"],
    ["stale", { value: 80, unit: "%", level: "stale" }, "80%", "stale"],
    ["unknown", { value: null, unit: "%", level: "unknown" }, "--", "unknown"],
  ])("shows the %s case with text and level from the backend", (_name, value, text, level) => {
    const vm = o2Vm(makeState(value), "live");
    expect(vm.text).toBe(text);
    expect(vm.level).toBe(level);
    expect(vm.color).toBe(theme.level[level].color);
    expect(vm.shape).toBe(theme.level[level].shape);
    expect(vm.word).toBe(theme.level[level].word);
  });

  it("shows caution with a diamond and warning with a triangle", () => {
    const caution = o2Vm(makeState({ value: 22, unit: "%", level: "caution" }), "live");
    expect(caution.word).toBe("CAUTION");
    expect(caution.shape).toBe("diamond");
    const warning = o2Vm(makeState({ value: 15, unit: "%", level: "warning" }), "live");
    expect(warning.word).toBe("WARNING");
    expect(warning.shape).toBe("triangle");
  });

  it("shows stale and unknown with their words", () => {
    expect(o2Vm(makeState({ value: 80, unit: "%", level: "stale" }), "live").word).toBe("STALE");
    expect(o2Vm(makeState({ value: null, unit: "%", level: "unknown" }), "live").word).toBe("NO DATA");
  });

  it("floors the value and never rounds it up", () => {
    expect(o2Vm(makeState({ value: 19.6, unit: "%", level: "caution" }), "live").text).toBe("19%");
  });

  it.each<[string, State | null]>([
    ["value null", makeState({ value: null, unit: "%", level: "nominal" })],
    // not makeState(undefined): that would fall back to the default value
    ["key missing", { ...makeState(), suit: { values: {}, faults: null } }],
    ["NaN", makeState({ value: Number.NaN, unit: "%", level: "nominal" })],
    ["Infinity", makeState({ value: Number.POSITIVE_INFINITY, unit: "%", level: "nominal" })],
    ["state null", null],
  ])("shows -- and unknown when there is no usable number (%s)", (_name, state) => {
    const vm = o2Vm(state, "live");
    expect(vm.text).toBe("--");
    expect(vm.level).toBe("unknown");
    expect(vm.color).toBe(theme.level.unknown.color);
  });

  it.each(["offline", "connecting"] as const)("forces stale and keeps the number when %s", (conn) => {
    const vm = o2Vm(makeState(), conn);
    expect(vm.text).toBe("92%");
    expect(vm.level).toBe("stale");
    expect(vm.color).toBe(theme.level.stale.color);
    expect(vm.color).not.toBe(theme.level.nominal.color);
    expect(vm.shape).toBe(theme.level.stale.shape);
    expect(vm.word).toBe(theme.level.stale.word);
  });

  it.each(["offline", "connecting"] as const)("shows -- and unknown when %s and there is no number", (conn) => {
    const vm = o2Vm(null, conn);
    expect(vm.text).toBe("--");
    expect(vm.level).toBe("unknown");
  });

  it("does not mutate its input", () => {
    const state = makeState();
    const copy = JSON.stringify(state);
    o2Vm(deepFreeze(state), "offline");
    expect(JSON.stringify(state)).toBe(copy);
  });
});
