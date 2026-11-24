// Consumables, bottom right: what the wearer is spending (oxygen, batteries, coolant) and what
// builds up (scrubber CO2), as bars with a mark at the warning limit from data/ranges.json.
import type { State } from "../contract.gen";
import type { BarRow, Conn, ConsumablesVm } from "./types";
import { rangeOf, readValue, valueRow } from "./values";

export const CONSUMABLES: readonly string[] = [
  "oxy_pri_storage",
  "oxy_sec_storage",
  "primary_battery_level",
  "secondary_battery_level",
  "scrubber_a_co2_storage",
  "scrubber_b_co2_storage",
  "coolant_storage",
];

/** Every consumable is a percentage, so every bar runs from 0 to 100. */
const FULL = 100;

const clamp01 = (x: number): number => Math.min(1, Math.max(0, x));

/** The edge that raises a warning: the minimum for a value checked low, the maximum for one checked high. */
function limitOf(name: string): number | null {
  const range = rangeOf(name);
  if (range === undefined) return null;
  return clamp01((range.check === "high" ? range.max : range.min) / FULL);
}

export function consumablesVm(state: State | null, conn: Conn): ConsumablesVm {
  const rows: BarRow[] = CONSUMABLES.map((name) => {
    const { value } = readValue(state, name, conn);
    return { ...valueRow(state, name, conn), fill: value === null ? 0 : clamp01(value / FULL), limit: limitOf(name) };
  });
  return { label: "CONSUMABLES", rows };
}
