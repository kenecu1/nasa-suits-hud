import { describe, expect, it } from "vitest";
import type { State } from "../contract.gen";
import { LEVELS, theme } from "../theme";
import { dcuVm } from "./dcu.vm";
import { buildHud } from "./hud";
import { linkVm } from "./link.vm";
import { o2Vm } from "./o2.vm";

function makeState(): State {
  return {
    type: "state",
    v: 2,
    seq: 1,
    t: 100,
    link: { tss: "ok", age_s: 0.2, mode: "sim" },
    eva: { started: false, elapsed_s: 0, phase: null },
    suit: { values: { oxy_pri_storage: { value: 92, unit: "%", level: "nominal" } }, faults: null },
    dcu: { batt: "LOCAL", oxy: "PRI", comm: "A", fan: "PRI", pump: "OPEN", co2: "A" },
    uia: null,
  };
}

describe("buildHud", () => {
  it.each(["live", "offline", "connecting"] as const)("returns the three panels for conn %s", (conn) => {
    const state = makeState();
    expect(buildHud(state, conn)).toEqual({
      o2: o2Vm(state, conn),
      dcu: dcuVm(state, conn),
      link: linkVm(state, conn),
    });
  });

  it("returns the three panels without a state", () => {
    expect(buildHud(null, "connecting")).toEqual({
      o2: o2Vm(null, "connecting"),
      dcu: dcuVm(null, "connecting"),
      link: linkVm(null, "connecting"),
    });
  });
});

describe("theme.level", () => {
  const styles = LEVELS.map((level) => theme.level[level]);

  it("covers five levels", () => {
    expect(styles).toHaveLength(5);
  });

  it("gives every level its own shape", () => {
    expect(new Set(styles.map((s) => s.shape)).size).toBe(5);
  });

  it("gives every level its own word", () => {
    expect(new Set(styles.map((s) => s.word)).size).toBe(5);
  });

  it("gives every level its own colour", () => {
    expect(new Set(styles.map((s) => s.color)).size).toBe(5);
  });
});
