// Test helper only (vitest runs *.test.ts files; this file is imported by them).
// One full, nominal State to build tests from, and a few helpers to change it.
import ranges from "../../../data/ranges.json";
import type { Alert, Level, State, SuitValue } from "../contract.gen";

/** Every telemetry name the backend sends: the ranged ones and the unranged ones. */
export const TELEMETRY_NAMES: readonly string[] = [...Object.keys(ranges.ranges), ...Object.keys(ranges.unranged)];

/** A value in the middle of its range, so it is nominal. */
const NOMINAL: Record<string, number> = {
  primary_battery_level: 80,
  secondary_battery_level: 90,
  oxy_pri_storage: 92,
  oxy_sec_storage: 85,
  oxy_pri_pressure: 3000,
  oxy_sec_pressure: 2900,
  coolant_storage: 95,
  heart_rate: 90,
  oxy_consumption: 0.1,
  co2_production: 0.1,
  suit_pressure_oxy: 3.95,
  suit_pressure_co2: 0.02,
  suit_pressure_other: 0.2,
  suit_pressure_total: 4.2,
  helmet_pressure_co2: 0.05,
  fan_pri_rpm: 30000,
  fan_sec_rpm: 0,
  scrubber_a_co2_storage: 20,
  scrubber_b_co2_storage: 25,
  temperature: 21.5,
  coolant_liquid_pressure: 400,
  coolant_gas_pressure: 300,
  eva_elapsed_time: 1312,
};

function unitOf(name: string): string {
  const ranged = (ranges.ranges as Record<string, { unit: string }>)[name];
  return ranged?.unit ?? (ranges.unranged as Record<string, { unit: string }>)[name]?.unit ?? "";
}

export function makeValue(value: number | null, level: Level, unit = ""): SuitValue {
  return { value, unit, level };
}

export function makeValues(): Record<string, SuitValue> {
  return Object.fromEntries(
    TELEMETRY_NAMES.map((name) => [name, makeValue(NOMINAL[name] ?? 0, name === "fan_sec_rpm" ? "off" : "nominal", unitOf(name))]),
  );
}

export function makeAlert(id: string, severity: Alert["severity"] = "warning", overrides: Partial<Alert> = {}): Alert {
  return { id, severity, title: `Title of ${id}`, action: `Do something about ${id}`, since: 100, acked: false, ...overrides };
}

export function makeState(overrides: Partial<State> = {}): State {
  return {
    type: "state",
    v: 2,
    seq: 1,
    t: 100,
    link: { tss: "ok", age_s: 0.2, mode: "sim", level: "nominal" },
    eva: { started: true, elapsed_s: 1312, phase: null },
    suit: { values: makeValues(), faults: null },
    dcu: { batt: "LOCAL", oxy: "PRI", comm: "A", fan: "PRI", pump: "OPEN", co2: "A" },
    uia: { eva_power: "ON", o2_supply: "OPEN", water_supply: "OPEN", water_waste: "CLOSED", o2_vent: "CLOSED", depress: "CLOSED" },
    alerts: [],
    ui: { details_open: false },
    ...overrides,
  };
}

/** A state with one telemetry value replaced. */
export function withValue(name: string, value: SuitValue | undefined, base: State = makeState()): State {
  return { ...base, suit: { ...base.suit, values: { ...base.suit.values, [name]: value } } };
}

/** Freeze an object and everything inside it, so a view model that writes to its input throws. */
export function deepFreeze<T>(value: T): T {
  if (typeof value === "object" && value !== null && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const inner of Object.values(value)) deepFreeze(inner);
  }
  return value;
}

/** A value the contract does not allow (a newer or broken backend), for the "does not trust" tests. */
export function loose<T>(value: unknown): T {
  return value as T;
}
