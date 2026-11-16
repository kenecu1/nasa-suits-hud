import { describe, expect, it } from "vitest";
import type { State } from "../contract.gen";
import { theme } from "../theme";
import { dcuVm } from "./dcu.vm";

function makeState(overrides: Partial<State> = {}): State {
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
    ...overrides,
  };
}

describe("dcuVm", () => {
  it("labels the panel O2 SWITCH", () => {
    expect(dcuVm(makeState(), "live").label).toBe("O2 SWITCH");
  });

  it.each(["PRI", "SEC"] as const)("shows %s as current in the text colour when live", (oxy) => {
    const state = makeState({ dcu: { batt: "LOCAL", oxy, comm: "A", fan: "PRI", pump: "OPEN", co2: "A" } });
    const vm = dcuVm(state, "live");
    expect(vm.text).toBe(oxy);
    expect(vm.current).toBe(true);
    expect(vm.color).toBe(theme.color.text);
  });

  it("shows -- and unknown colour when dcu is null", () => {
    const vm = dcuVm(makeState({ dcu: null }), "live");
    expect(vm.text).toBe("--");
    expect(vm.current).toBe(false);
    expect(vm.color).toBe(theme.level.unknown.color);
  });

  it("shows -- and unknown colour when state is null", () => {
    const vm = dcuVm(null, "live");
    expect(vm.text).toBe("--");
    expect(vm.current).toBe(false);
    expect(vm.color).toBe(theme.level.unknown.color);
  });

  it.each(["offline", "connecting"] as const)("keeps the position but marks it not current when %s", (conn) => {
    const vm = dcuVm(makeState(), conn);
    expect(vm.text).toBe("PRI");
    expect(vm.current).toBe(false);
    expect(vm.color).toBe(theme.level.stale.color);
  });

  it.each(["BOGUS", "", 3, { a: 1 }])("shows -- for a position that is not PRI or SEC (%j)", (oxy) => {
    const state = makeState();
    const odd = { ...state, dcu: { ...state.dcu, oxy } } as unknown as State;
    const vm = dcuVm(odd, "live");
    expect(vm.text).toBe("--");
    expect(vm.current).toBe(false);
    expect(vm.color).toBe(theme.level.unknown.color);
  });
});
