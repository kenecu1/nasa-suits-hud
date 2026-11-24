import { describe, expect, it } from "vitest";
import type { Alert, State } from "../contract.gen";
import { deepFreeze, loose, makeAlert, makeState } from "./testState";
import type { Conn } from "./types";
import { toneVm } from "./tone.vm";

const stateWith = (alerts: Alert[], extra: Partial<State> = {}): State => makeState({ alerts, ...extra });

describe("toneVm", () => {
  it("plays for a warning that was not in the previous state", () => {
    const vm = toneVm(stateWith([makeAlert("o2_low")]), stateWith([]), "live");
    expect(vm.play).toBe(true);
    expect(vm.newWarnings).toEqual(["o2_low"]);
  });

  it("plays for a warning when there is no previous state at all", () => {
    expect(toneVm(stateWith([makeAlert("o2_low")]), null, "live")).toMatchObject({ play: true, newWarnings: ["o2_low"] });
  });

  it("does not play when the same warning was already in the previous state", () => {
    const vm = toneVm(stateWith([makeAlert("o2_low")]), stateWith([makeAlert("o2_low")]), "live");
    expect(vm.play).toBe(false);
    expect(vm.newWarnings).toEqual([]);
  });

  it("does not play when the previous warning was acknowledged meanwhile", () => {
    const prev = stateWith([makeAlert("o2_low")]);
    const now = stateWith([makeAlert("o2_low", "warning", { acked: true })]);
    expect(toneVm(now, prev, "live").play).toBe(false);
  });

  it("plays when a caution of the same id escalates to a warning", () => {
    const prev = stateWith([makeAlert("o2_low", "caution")]);
    const now = stateWith([makeAlert("o2_low", "warning")]);
    expect(toneVm(now, prev, "live")).toMatchObject({ play: true, newWarnings: ["o2_low"] });
  });

  it("does not play when a warning eases to a caution", () => {
    const prev = stateWith([makeAlert("o2_low", "warning")]);
    const now = stateWith([makeAlert("o2_low", "caution")]);
    expect(toneVm(now, prev, "live").play).toBe(false);
  });

  it("does not play for an acknowledged warning, even a new one", () => {
    const now = stateWith([makeAlert("o2_low", "warning", { acked: true })]);
    expect(toneVm(now, stateWith([]), "live")).toMatchObject({ play: false, newWarnings: [] });
  });

  it("does not play for cautions only", () => {
    const now = stateWith([makeAlert("c1", "caution"), makeAlert("c2", "caution")]);
    expect(toneVm(now, stateWith([]), "live")).toMatchObject({ play: false, newWarnings: [] });
  });

  it("does not play without alerts", () => {
    expect(toneVm(stateWith([]), stateWith([]), "live").play).toBe(false);
  });

  it("lists only the new warnings, sorted, when others were there before", () => {
    const prev = stateWith([makeAlert("b_old")]);
    const now = stateWith([makeAlert("z_new"), makeAlert("b_old"), makeAlert("a_new")]);
    expect(toneVm(now, prev, "live")).toMatchObject({ play: true, newWarnings: ["a_new", "z_new"] });
  });

  it.each<Conn>(["offline", "connecting"])("does not play when conn is %s", (conn) => {
    const vm = toneVm(stateWith([makeAlert("o2_low")]), stateWith([]), conn);
    expect(vm).toMatchObject({ play: false, newWarnings: [] });
  });

  it("does not play without a state", () => {
    expect(toneVm(null, null, "live")).toEqual({ play: false, key: "none", newWarnings: [] });
  });

  it("does not play when the state has no alerts list", () => {
    const state = loose<State>({ ...makeState(), alerts: undefined });
    expect(toneVm(state, null, "live").play).toBe(false);
  });

  describe("key", () => {
    it("differs between states with a different seq", () => {
      const a = toneVm(makeState({ seq: 1, t: 100 }), null, "live").key;
      const b = toneVm(makeState({ seq: 2, t: 100 }), null, "live").key;
      expect(a).not.toBe(b);
    });

    it("differs between states with a different t", () => {
      const a = toneVm(makeState({ seq: 1, t: 100 }), null, "live").key;
      const b = toneVm(makeState({ seq: 1, t: 101 }), null, "live").key;
      expect(a).not.toBe(b);
    });

    it("is equal for the same state, so a rebuild does not replay", () => {
      const state = stateWith([makeAlert("o2_low")], { seq: 7, t: 123 });
      const first = toneVm(state, stateWith([]), "live");
      const again = toneVm(state, stateWith([]), "live");
      expect(again.key).toBe(first.key);
    });

    it("does not depend on the previous state", () => {
      const state = stateWith([makeAlert("o2_low")], { seq: 7, t: 123 });
      expect(toneVm(state, null, "live").key).toBe(toneVm(state, stateWith([]), "live").key);
    });

    it("is the same whatever conn says", () => {
      const state = makeState({ seq: 4, t: 9 });
      expect(toneVm(state, null, "offline").key).toBe(toneVm(state, null, "live").key);
    });
  });

  it("does not change its inputs", () => {
    const now = deepFreeze(stateWith([makeAlert("o2_low")]));
    const prev = deepFreeze(stateWith([]));
    expect(() => toneVm(now, prev, "live")).not.toThrow();
  });
});
