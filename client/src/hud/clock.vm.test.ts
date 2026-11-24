import { describe, expect, it } from "vitest";
import type { Eva } from "../contract.gen";
import { theme } from "../theme";
import { clockVm } from "./clock.vm";
import { deepFreeze, loose, makeState } from "./testState";
import type { Conn } from "./types";

const evaState = (eva: Partial<Eva>) => makeState({ eva: { started: true, elapsed_s: 0, phase: null, ...eva } });

describe("clockVm", () => {
  it("labels the clock EVA", () => {
    expect(clockVm(makeState(), "live").label).toBe("EVA");
  });

  it("writes 1312 s as 00:21:52 in the text colour", () => {
    expect(clockVm(evaState({ elapsed_s: 1312 }), "live")).toEqual({ label: "EVA", text: "00:21:52", color: theme.color.text });
  });

  it.each<[number, string]>([
    [0, "00:00:00"],
    [3599, "00:59:59"],
    [3600, "01:00:00"],
    [36000, "10:00:00"],
    [1312.9, "00:21:52"],
  ])("writes %s s as %s", (seconds, text) => {
    expect(clockVm(evaState({ elapsed_s: seconds }), "live").text).toBe(text);
  });

  it("says NOT STARTED when started is false, whatever elapsed says", () => {
    const vm = clockVm(evaState({ started: false, elapsed_s: 500 }), "live");
    expect(vm).toEqual({ label: "EVA", text: "NOT STARTED", color: theme.color.text });
  });

  it("says NOT STARTED when started is false and elapsed is null", () => {
    expect(clockVm(evaState({ started: false, elapsed_s: null }), "live").text).toBe("NOT STARTED");
  });

  it("shows --:--:-- with the unknown colour when started is null and elapsed is null", () => {
    expect(clockVm(evaState({ started: null, elapsed_s: null }), "live")).toEqual({
      label: "EVA",
      text: "--:--:--",
      color: theme.level.unknown.color,
    });
  });

  it("shows --:--:-- with the unknown colour when started but elapsed is null", () => {
    const vm = clockVm(evaState({ started: true, elapsed_s: null }), "live");
    expect(vm).toMatchObject({ text: "--:--:--", color: theme.level.unknown.color });
  });

  it.each([Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])("shows --:--:-- for elapsed %s", (elapsed) => {
    expect(clockVm(evaState({ elapsed_s: elapsed }), "live")).toMatchObject({ text: "--:--:--", color: theme.level.unknown.color });
  });

  it("shows --:--:-- for an elapsed that is not a number", () => {
    const state = makeState({ eva: loose({ started: true, elapsed_s: "1312", phase: null }) });
    expect(clockVm(state, "live").text).toBe("--:--:--");
  });

  it("shows --:--:-- with the unknown colour without a state", () => {
    expect(clockVm(null, "connecting")).toEqual({ label: "EVA", text: "--:--:--", color: theme.level.unknown.color });
  });

  it("shows --:--:-- when the state has no eva block", () => {
    expect(clockVm(loose({ ...makeState(), eva: undefined }), "live").text).toBe("--:--:--");
  });

  it.each<Conn>(["offline", "connecting"])("uses the stale colour and keeps the time when conn is %s", (conn) => {
    expect(clockVm(makeState(), conn)).toEqual({ label: "EVA", text: "00:21:52", color: theme.level.stale.color });
  });

  it("uses the stale colour for NOT STARTED when offline", () => {
    const vm = clockVm(evaState({ started: false }), "offline");
    expect(vm).toMatchObject({ text: "NOT STARTED", color: theme.level.stale.color });
  });

  it("keeps the unknown colour for a missing time even when offline", () => {
    expect(clockVm(evaState({ elapsed_s: null }), "offline")).toMatchObject({ text: "--:--:--", color: theme.level.unknown.color });
  });

  it("does not change its input", () => {
    expect(() => clockVm(deepFreeze(makeState()), "live")).not.toThrow();
  });
});
