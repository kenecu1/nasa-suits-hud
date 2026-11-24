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
    link: { tss: "ok", age_s: 0.2, mode: "sim", level: "nominal" },
    eva: { started: false, elapsed_s: 0, phase: null },
    suit: { values: { oxy_pri_storage: { value: 92, unit: "%", level: "nominal" } }, faults: null },
    dcu: { batt: "LOCAL", oxy: "PRI", comm: "A", fan: "PRI", pump: "OPEN", co2: "A" },
    uia: null,
    alerts: [],
    ui: { details_open: false },
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

  it("puts each view model under its own key, with the words the wearer reads", () => {
    const live = buildHud(makeState(), "live");
    expect(live.o2).toMatchObject({ label: "O2 PRI", text: "92%", word: "NOMINAL", shape: "circle" });
    expect(live.dcu).toMatchObject({ label: "O2 SWITCH", text: "PRI", current: true });
    expect(live.link).toMatchObject({ label: "LINK", text: "TSS OK", mode: "SIM", status: "ok" });

    const offline = buildHud(makeState(), "offline");
    expect(offline.o2).toMatchObject({ text: "92%", word: "STALE", shape: "square" });
    expect(offline.dcu).toMatchObject({ text: "PRI", current: false });
    expect(offline.link).toMatchObject({ text: "OFFLINE", word: "WARNING", shape: "triangle" });
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

  it("has a style for exactly the five levels of the contract", () => {
    expect(Object.keys(theme.level).sort()).toEqual(["caution", "nominal", "stale", "unknown", "warning"]);
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
