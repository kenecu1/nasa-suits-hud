import { describe, expect, it } from "vitest";
import type { Level, LinkStatus, Mode, State } from "../contract.gen";
import { theme } from "../theme";
import { linkVm } from "./link.vm";

function makeState(tss: LinkStatus = "ok", mode: Mode = "sim"): State {
  return {
    type: "state",
    v: 2,
    seq: 1,
    t: 100,
    link: { tss, age_s: 0.2, mode },
    eva: { started: false, elapsed_s: 0, phase: null },
    suit: { values: { oxy_pri_storage: { value: 92, unit: "%", level: "nominal" } }, faults: null },
    dcu: { batt: "LOCAL", oxy: "PRI", comm: "A", fan: "PRI", pump: "OPEN", co2: "A" },
    uia: null,
  };
}

function expectLook(vm: ReturnType<typeof linkVm>): void {
  const look = theme.level[vm.level];
  expect(vm.color).toBe(look.color);
  expect(vm.shape).toBe(look.shape);
  expect(vm.word).toBe(look.word);
}

describe("linkVm", () => {
  it("labels the line LINK", () => {
    expect(linkVm(makeState(), "live").label).toBe("LINK");
  });

  it("says CONNECTING with unknown level and no mode before the first state", () => {
    const vm = linkVm(null, "connecting");
    expect(vm.status).toBe("connecting");
    expect(vm.text).toBe("CONNECTING");
    expect(vm.level).toBe("unknown");
    expect(vm.mode).toBeNull();
    expectLook(vm);
  });

  it("treats live with no state like connecting", () => {
    expect(linkVm(null, "live")).toEqual(linkVm(null, "connecting"));
  });

  it("says OFFLINE as a warning even if the last state said ok, and keeps the last mode", () => {
    const vm = linkVm(makeState("ok", "sim"), "offline");
    expect(vm.status).toBe("offline");
    expect(vm.text).toBe("OFFLINE");
    expect(vm.level).toBe("warning");
    expect(vm.mode).toBe("SIM");
    expectLook(vm);
  });

  it("has no mode when offline without any state", () => {
    const vm = linkVm(null, "offline");
    expect(vm.status).toBe("offline");
    expect(vm.mode).toBeNull();
  });

  it.each<[LinkStatus, string, Level]>([
    ["ok", "TSS OK", "nominal"],
    ["unreachable", "TSS UNREACHABLE", "warning"],
    ["unassigned", "TSS NOT ASSIGNED", "warning"],
    ["bad_data", "TSS BAD DATA", "warning"],
    ["stale", "TSS STALE", "stale"],
  ])("maps live status %s to text %s and level %s", (tss, text, level) => {
    const vm = linkVm(makeState(tss), "live");
    expect(vm.status).toBe(tss);
    expect(vm.text).toBe(text);
    expect(vm.level).toBe(level);
    expectLook(vm);
  });

  it.each<[Mode, string]>([
    ["sim", "SIM"],
    ["replay", "REPLAY"],
    ["live", "LIVE"],
  ])("shows mode %s in upper case", (mode, expected) => {
    expect(linkVm(makeState("ok", mode), "live").mode).toBe(expected);
  });

  it.each(["rebooting", "toString", "constructor"])("shows a status it does not know (%s) as a warning", (tss) => {
    const state = makeState();
    const odd = { ...state, link: { ...state.link, tss } } as unknown as State;
    const vm = linkVm(odd, "live");
    expect(vm.text).toBe(`TSS ${tss.toUpperCase()}`);
    expect(vm.level).toBe("warning");
    expect(vm).toMatchObject(theme.level.warning);
  });
});
