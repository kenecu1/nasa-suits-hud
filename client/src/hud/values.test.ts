import { describe, expect, it } from "vitest";
import type { Level, State, SuitValue } from "../contract.gen";
import { theme } from "../theme";
import { loose, makeState, makeValue, withValue } from "./testState";
import type { Conn } from "./types";
import { formatDuration, formatNumber, isLevel, NO_NUMBER, rangeOf, readValue, VALUE_FORMAT, valueRow, valueText } from "./values";

describe("isLevel", () => {
  it.each(["nominal", "caution", "warning", "unknown", "stale", "off"])("accepts %s", (level) => {
    expect(isLevel(level)).toBe(true);
  });

  it.each(["critical", "toString", "constructor", "__proto__", "", "NOMINAL"])("refuses the word %j", (word) => {
    expect(isLevel(word)).toBe(false);
  });

  it.each([null, undefined, 3, {}, []])("refuses a non-string (%j)", (value) => {
    expect(isLevel(value)).toBe(false);
  });
});

describe("readValue", () => {
  it("reads a usable value with its unit and the backend's level when live", () => {
    expect(readValue(makeState(), "oxy_pri_storage", "live")).toEqual({ value: 92, unit: "%", level: "nominal" });
  });

  it.each<[string, number | null]>([
    ["null", null],
    ["NaN", Number.NaN],
    ["Infinity", Number.POSITIVE_INFINITY],
    ["-Infinity", Number.NEGATIVE_INFINITY],
  ])("gives no number and an unknown level for %s", (_name, value) => {
    const state = withValue("oxy_pri_storage", makeValue(value, "nominal", "%"));
    expect(readValue(state, "oxy_pri_storage", "live")).toEqual({ value: null, unit: "%", level: "unknown" });
  });

  it("gives no number for a value that is not a number at all", () => {
    const state = withValue("oxy_pri_storage", loose<SuitValue>({ value: "92", unit: "%", level: "nominal" }));
    expect(readValue(state, "oxy_pri_storage", "live").value).toBeNull();
  });

  it.each(["critical", "toString", "constructor", ""])("refuses the level word %j and shows unknown", (word) => {
    const state = withValue("oxy_pri_storage", loose({ value: 92, unit: "%", level: word }));
    expect(readValue(state, "oxy_pri_storage", "live")).toEqual({ value: null, unit: "%", level: "unknown" });
  });

  it("gives no number for a name the state does not have", () => {
    expect(readValue(makeState(), "no_such_value", "live")).toEqual({ value: null, unit: "", level: "unknown" });
  });

  it.each(["toString", "constructor", "__proto__"])("does not read the inherited key %s", (name) => {
    expect(readValue(makeState(), name, "live").value).toBeNull();
  });

  it("gives no number without a state", () => {
    expect(readValue(null, "oxy_pri_storage", "live")).toEqual({ value: null, unit: "", level: "unknown" });
  });

  it("treats a missing unit as empty", () => {
    const state = withValue("heart_rate", loose({ value: 70, level: "nominal" }));
    expect(readValue(state, "heart_rate", "live").unit).toBe("");
  });

  it.each<Conn>(["offline", "connecting"])("is stale with the number kept when conn is %s", (conn) => {
    expect(readValue(makeState(), "oxy_pri_storage", conn)).toEqual({ value: 92, unit: "%", level: "stale" });
  });

  it("keeps a value with level off when live", () => {
    const state = withValue("fan_sec_rpm", makeValue(0, "off", "rpm"));
    expect(readValue(state, "fan_sec_rpm", "live")).toEqual({ value: 0, unit: "rpm", level: "off" });
  });

  it("makes a value with level off stale when offline", () => {
    const state = withValue("fan_sec_rpm", makeValue(0, "off", "rpm"));
    expect(readValue(state, "fan_sec_rpm", "offline").level).toBe("stale");
  });

  it("keeps the number of a stale value from the backend", () => {
    const state = withValue("oxy_pri_storage", makeValue(55, "stale", "%"));
    expect(readValue(state, "oxy_pri_storage", "live")).toEqual({ value: 55, unit: "%", level: "stale" });
  });

  it("keeps zero as a number", () => {
    const state = withValue("oxy_pri_storage", makeValue(0, "warning", "%"));
    expect(readValue(state, "oxy_pri_storage", "live").value).toBe(0);
  });
});

describe("rangeOf", () => {
  it("returns the entry of data/ranges.json", () => {
    expect(rangeOf("oxy_pri_storage")).toMatchObject({ min: 20, max: 100, check: "low" });
    expect(rangeOf("scrubber_a_co2_storage")).toMatchObject({ min: 0, max: 60, check: "high" });
  });

  it.each(["eva_elapsed_time", "nope", "toString", "constructor"])("has no entry for %s", (name) => {
    expect(rangeOf(name)).toBeUndefined();
  });
});

describe("formatNumber", () => {
  it.each<[number, number, "floor" | "ceil" | "round", string]>([
    [19.6, 0, "floor", "19"],
    [19.6, 0, "ceil", "20"],
    [19.4, 0, "round", "19"],
    [19.5, 0, "round", "20"],
    [3.951, 2, "floor", "3.95"],
    [3.951, 2, "ceil", "3.96"],
    [0, 3, "round", "0.000"],
    [-0.001, 2, "round", "0.00"],
    [1234567, 0, "round", "1234567"],
  ])("formats %s with %s decimals, %s -> %s", (value, decimals, rounding, expected) => {
    expect(formatNumber(value, decimals, rounding)).toBe(expected);
  });

  it("is not fooled by binary floating point (1.1 * 100 is 110.00000000000001)", () => {
    expect(formatNumber(1.1, 2, "ceil")).toBe("1.10");
    expect(formatNumber(0.29, 2, "floor")).toBe("0.29");
  });
});

describe("formatDuration", () => {
  it.each<[number, string]>([
    [0, "00:00:00"],
    [59, "00:00:59"],
    [60, "00:01:00"],
    [1312, "00:21:52"],
    [3600, "01:00:00"],
    [3661, "01:01:01"],
    [360000, "100:00:00"],
    [59.9, "00:00:59"],
    [-5, "00:00:00"],
  ])("writes %s s as %s", (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected);
  });
});

describe("valueText", () => {
  it("is -- without a number", () => {
    expect(valueText("oxy_pri_storage", null, "%")).toBe(NO_NUMBER);
    expect(NO_NUMBER).toBe("--");
  });

  it("glues % to the number", () => {
    expect(valueText("oxy_pri_storage", 92, "%")).toBe("92%");
  });

  it("puts a space before other units", () => {
    expect(valueText("suit_pressure_oxy", 3.95, "psi")).toBe("3.95 psi");
    expect(valueText("fan_pri_rpm", 30000, "rpm")).toBe("30000 rpm");
    expect(valueText("temperature", 21.54, "°C")).toBe("21.5 °C");
  });

  it("writes no unit when there is none", () => {
    expect(valueText("heart_rate", 70, "")).toBe("70");
  });

  it("uses the decimals of the format", () => {
    expect(valueText("oxy_consumption", 0.1, "psi/min")).toBe("0.10 psi/min");
    expect(valueText("suit_pressure_co2", 0.02, "psi")).toBe("0.020 psi");
  });

  it("floors a value checked low, so 19.6% never reads as 20%", () => {
    expect(valueText("oxy_pri_storage", 19.6, "%")).toBe("19%");
  });

  it("rounds a value checked high up, so 60.2% never reads as 60%", () => {
    expect(valueText("scrubber_a_co2_storage", 60.2, "%")).toBe("61%");
  });

  it("rounds a value checked both ways to the nearest", () => {
    expect(valueText("heart_rate", 90.4, "bpm")).toBe("90 bpm");
    expect(valueText("heart_rate", 90.6, "bpm")).toBe("91 bpm");
  });

  it("rounds a name without a range to the nearest", () => {
    expect(valueText("brand_new_value", 1.004, "x")).toBe("1.00 x");
    expect(valueText("brand_new_value", 1.006, "x")).toBe("1.01 x");
  });

  it("writes the EVA time as h:mm:ss, padded", () => {
    expect(valueText("eva_elapsed_time", 1312, "s")).toBe("00:21:52");
  });
});

describe("valueRow", () => {
  it("combines name, label, text and the look of the level", () => {
    expect(valueRow(makeState(), "oxy_pri_storage", "live")).toEqual({
      name: "oxy_pri_storage",
      label: "O2 PRI",
      text: "92%",
      level: "nominal",
      ...theme.level.nominal,
    });
  });

  it.each<Level>(["nominal", "caution", "warning", "stale", "off"])("takes colour, shape and word of the level %s", (level) => {
    const state = withValue("heart_rate", makeValue(70, level, "bpm"));
    const row = valueRow(state, "heart_rate", "live");
    expect(row).toMatchObject({ level, ...theme.level[level] });
  });

  it("shows -- and the unknown look without a usable number", () => {
    const state = withValue("heart_rate", makeValue(null, "unknown", "bpm"));
    expect(valueRow(state, "heart_rate", "live")).toMatchObject({ text: "--", level: "unknown", ...theme.level.unknown });
  });

  it("shows -- and the unknown look for a missing name", () => {
    expect(valueRow(makeState(), "heart_rate_typo", "live")).toMatchObject({ text: "--", level: "unknown", ...theme.level.unknown });
  });

  it("shows -- and the unknown look without a state", () => {
    expect(valueRow(null, "heart_rate", "live")).toMatchObject({ label: "HEART", text: "--", level: "unknown" });
  });

  it.each<Conn>(["offline", "connecting"])("keeps the number and shows the stale look when conn is %s", (conn) => {
    expect(valueRow(makeState(), "oxy_pri_storage", conn)).toMatchObject({ text: "92%", level: "stale", ...theme.level.stale });
  });

  it("passes level off through when live and makes it stale when offline", () => {
    const state: State = makeState();
    expect(valueRow(state, "fan_sec_rpm", "live")).toMatchObject({ level: "off", ...theme.level.off });
    expect(valueRow(state, "fan_sec_rpm", "offline")).toMatchObject({ level: "stale", ...theme.level.stale });
  });

  it("labels a name that has no format with its upper-cased name", () => {
    const state = withValue("brand_new_value", makeValue(1.5, "nominal", "x"));
    expect(valueRow(state, "brand_new_value", "live")).toMatchObject({ label: "BRAND_NEW_VALUE", text: "1.50 x" });
  });

  it("does not take a label from the prototype", () => {
    expect(valueRow(makeState(), "toString", "live").label).toBe("TOSTRING");
  });

  it("writes the EVA time of a state value as h:mm:ss", () => {
    expect(valueRow(makeState(), "eva_elapsed_time", "live")).toMatchObject({ label: "EVA TIME", text: "00:21:52" });
  });
});

describe("VALUE_FORMAT", () => {
  it("has a format for every telemetry name of the contract", () => {
    const state = makeState();
    for (const name of Object.keys(state.suit.values)) expect(VALUE_FORMAT, name).toHaveProperty(name);
  });

  it("gives every name its own label", () => {
    const labels = Object.values(VALUE_FORMAT).map((f) => f.label);
    expect(new Set(labels).size).toBe(labels.length);
  });
});
