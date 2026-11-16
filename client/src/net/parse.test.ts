import { describe, expect, it } from "vitest";
import type { State } from "../contract.gen";
import { parseState } from "./parse";

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

function expectError(raw: unknown): string {
  const result = parseState(raw);
  expect("error" in result).toBe(true);
  if (!("error" in result)) throw new Error("expected an error");
  expect(typeof result.error).toBe("string");
  expect(result.error.length).toBeGreaterThan(0);
  return result.error;
}

function withChange(change: Record<string, unknown>): string {
  return JSON.stringify({ ...makeState(), ...change });
}

describe("parseState", () => {
  it("returns the state for a valid JSON string", () => {
    const state = makeState();
    expect(parseState(JSON.stringify(state))).toEqual({ state });
  });

  it("accepts extra unknown top-level fields", () => {
    const result = parseState(withChange({ future_field: { a: 1 } }));
    expect("state" in result).toBe(true);
  });

  it("rejects an ArrayBuffer", () => {
    expectError(new ArrayBuffer(8));
  });

  it("rejects a number", () => {
    expectError(5);
  });

  it("rejects text that is not JSON", () => {
    expectError("{not json");
  });

  it.each(["5", "null", "[]"])("rejects JSON that is not an object: %s", (text) => {
    expectError(text);
  });

  it("rejects a type other than state", () => {
    expectError(withChange({ type: "ack" }));
  });

  it("rejects another version and mentions the version", () => {
    expect(expectError(withChange({ v: 3 }))).toMatch(/version/i);
  });

  it("rejects a missing link", () => {
    const raw: Record<string, unknown> = { ...makeState() };
    delete raw.link;
    expectError(JSON.stringify(raw));
  });

  it("rejects a link.tss that is not a string", () => {
    expectError(withChange({ link: { tss: 5, age_s: 0.2, mode: "sim" } }));
  });

  it("rejects a missing suit", () => {
    const raw: Record<string, unknown> = { ...makeState() };
    delete raw.suit;
    expectError(JSON.stringify(raw));
  });

  it("rejects suit.values that is not an object", () => {
    expectError(withChange({ suit: { values: 5, faults: null } }));
  });
});
