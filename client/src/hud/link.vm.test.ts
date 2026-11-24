import { describe, expect, it } from "vitest";
import type { Level, LinkStatus, Mode, State } from "../contract.gen";
import { theme } from "../theme";
import { linkVm } from "./link.vm";
import { deepFreeze, loose, makeState } from "./testState";

function linkState(tss: LinkStatus = "ok", mode: Mode = "sim", level: Level = "nominal"): State {
  return makeState({ link: { tss, age_s: 0.2, mode, level } });
}

function expectLook(vm: ReturnType<typeof linkVm>): void {
  const look = theme.level[vm.level];
  expect(vm.color).toBe(look.color);
  expect(vm.shape).toBe(look.shape);
  expect(vm.word).toBe(look.word);
}

describe("linkVm", () => {
  it("labels the line LINK", () => {
    expect(linkVm(linkState(), "live").label).toBe("LINK");
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

  it("says CONNECTING while connecting even when an old state is given", () => {
    const vm = linkVm(linkState("ok", "sim", "nominal"), "connecting");
    expect(vm.text).toBe("CONNECTING");
    expect(vm.level).toBe("unknown");
    expect(vm.mode).toBe("SIM");
  });

  it("says OFFLINE as a warning even if the last state said ok, and keeps the last mode", () => {
    const vm = linkVm(linkState("ok", "sim"), "offline");
    expect(vm.status).toBe("offline");
    expect(vm.text).toBe("OFFLINE");
    expect(vm.level).toBe("warning");
    expect(vm.mode).toBe("SIM");
    expectLook(vm);
  });

  it("decides OFFLINE itself: the backend's own level does not matter", () => {
    const vm = linkVm(linkState("ok", "sim", "nominal"), "offline");
    expect(vm).toMatchObject({ level: "warning", ...theme.level.warning });
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
  ])("maps live status %s to text %s and the backend's level %s", (tss, text, level) => {
    const vm = linkVm(linkState(tss, "sim", level), "live");
    expect(vm.status).toBe(tss);
    expect(vm.text).toBe(text);
    expect(vm.level).toBe(level);
    expectLook(vm);
  });

  it.each<Level>(["nominal", "caution", "warning", "unknown", "stale", "off"])(
    "uses the level %s that the backend sent, not one decided from the status",
    (level) => {
      const vm = linkVm(linkState("ok", "sim", level), "live");
      expect(vm.level).toBe(level);
      expect(vm).toMatchObject(theme.level[level]);
    },
  );

  it.each(["critical", "", "toString", "constructor", "NOMINAL"])("shows a level word it does not know (%j) as a warning", (word) => {
    const state = makeState({ link: loose({ tss: "ok", age_s: 0.2, mode: "sim", level: word }) });
    const vm = linkVm(state, "live");
    expect(vm.level).toBe("warning");
    expect(vm).toMatchObject(theme.level.warning);
  });

  it("shows a missing level as a warning", () => {
    const state = makeState({ link: loose({ tss: "ok", age_s: 0.2, mode: "sim" }) });
    expect(linkVm(state, "live").level).toBe("warning");
  });

  it.each<[Mode, string]>([
    ["sim", "SIM"],
    ["replay", "REPLAY"],
    ["live", "LIVE"],
  ])("shows mode %s in upper case", (mode, expected) => {
    expect(linkVm(linkState("ok", mode), "live").mode).toBe(expected);
  });

  it.each(["rebooting", "toString", "constructor"])("shows a status it does not know (%s) as a warning", (tss) => {
    const state = makeState({ link: loose({ tss, age_s: 0.2, mode: "sim", level: "nominal" }) });
    const vm = linkVm(state, "live");
    expect(vm.text).toBe(`TSS ${tss.toUpperCase()}`);
    expect(vm.status).toBe(tss);
  });

  it("does not change its input", () => {
    expect(() => linkVm(deepFreeze(linkState()), "live")).not.toThrow();
  });
});
