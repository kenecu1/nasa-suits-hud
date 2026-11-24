// Reading one telemetry value out of the State, and writing it as text. Shared by the
// consumables, vitals and details view models. The backend decides every level; the client
// only refuses to show what it cannot trust (no number, a level it does not know, or a
// backend it no longer hears).
import ranges from "../../../data/ranges.json";
import type { Level, State } from "../contract.gen";
import { theme } from "../theme";
import type { Conn, LevelLook, ValueRow } from "./types";

export const NO_NUMBER = "--";

export function isLevel(value: unknown): value is Level {
  return typeof value === "string" && Object.hasOwn(theme.level, value);
}

export function lookOf(level: Level): LevelLook {
  return { level, ...theme.level[level] };
}

interface Reading {
  /** A finite number with a level this client can draw, or null. */
  value: number | null;
  unit: string;
  level: Level;
}

export function readValue(state: State | null, name: string, conn: Conn): Reading {
  const reading = state?.suit.values[name];
  const raw = reading?.value;
  const usable = typeof raw === "number" && Number.isFinite(raw) && isLevel(reading?.level);
  const unit = typeof reading?.unit === "string" ? reading.unit : "";
  if (!usable) return { value: null, unit, level: "unknown" };
  // A number from a backend we no longer hear is stale, whatever level it had.
  return { value: raw, unit, level: conn === "live" ? (reading?.level ?? "unknown") : "stale" };
}

type Rounding = "floor" | "ceil" | "round";

interface RangeEntry {
  min: number;
  max: number;
  check: "low" | "high" | "both";
}

const RANGED: Readonly<Record<string, RangeEntry | undefined>> = ranges.ranges as Record<string, RangeEntry>;

/** The range entry of a value, from data/ranges.json (the file the backend classifies with). */
export function rangeOf(name: string): RangeEntry | undefined {
  return Object.hasOwn(RANGED, name) ? RANGED[name] : undefined;
}

/**
 * Round toward the limit that matters, so the text never looks safer than the value: a value
 * checked low is floored (19.6% must not read "20%" when 20 is the limit), one checked high is
 * rounded up, anything else to the nearest.
 */
function roundingOf(name: string): Rounding {
  const check = rangeOf(name)?.check;
  if (check === "low") return "floor";
  if (check === "high") return "ceil";
  return "round";
}

export function formatNumber(value: number, decimals: number, rounding: Rounding): string {
  const scale = 10 ** decimals;
  const scaled = Math[rounding](Number((value * scale).toPrecision(12)));
  return (scaled / scale).toFixed(decimals);
}

/** Seconds as h:mm:ss, never negative. */
export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** How each telemetry value is named and written on the HUD. Names are the contract's. */
interface ValueFormat {
  label: string;
  decimals: number;
  duration?: true;
}

export const VALUE_FORMAT: Readonly<Record<string, ValueFormat>> = {
  oxy_pri_storage: { label: "O2 PRI", decimals: 0 },
  oxy_sec_storage: { label: "O2 SEC", decimals: 0 },
  oxy_pri_pressure: { label: "PRI PSI", decimals: 0 },
  oxy_sec_pressure: { label: "SEC PSI", decimals: 0 },
  oxy_consumption: { label: "O2 USE", decimals: 3 },
  primary_battery_level: { label: "BATT PRI", decimals: 0 },
  secondary_battery_level: { label: "BATT SEC", decimals: 0 },
  suit_pressure_oxy: { label: "SUIT O2", decimals: 2 },
  suit_pressure_co2: { label: "SUIT CO2", decimals: 3 },
  suit_pressure_other: { label: "OTHER", decimals: 2 },
  suit_pressure_total: { label: "TOTAL", decimals: 2 },
  helmet_pressure_co2: { label: "HELM CO2", decimals: 3 },
  co2_production: { label: "CO2 MADE", decimals: 3 },
  fan_pri_rpm: { label: "FAN PRI", decimals: 0 },
  fan_sec_rpm: { label: "FAN SEC", decimals: 0 },
  scrubber_a_co2_storage: { label: "SCRUB A", decimals: 0 },
  scrubber_b_co2_storage: { label: "SCRUB B", decimals: 0 },
  coolant_storage: { label: "COOLANT", decimals: 0 },
  coolant_liquid_pressure: { label: "LIQ PSI", decimals: 0 },
  coolant_gas_pressure: { label: "GAS PSI", decimals: 0 },
  heart_rate: { label: "HEART", decimals: 0 },
  temperature: { label: "TEMP", decimals: 1 },
  eva_elapsed_time: { label: "EVA TIME", decimals: 0, duration: true },
};

/** A name this client has no format for (a newer backend): shown under its own name, not hidden. */
function formatOf(name: string): ValueFormat {
  return Object.hasOwn(VALUE_FORMAT, name) ? (VALUE_FORMAT[name] as ValueFormat) : { label: name.toUpperCase(), decimals: 2 };
}

/** "92%" for a percentage, "3.95 psi" otherwise; "--" without a number. */
export function valueText(name: string, value: number | null, unit: string): string {
  if (value === null) return NO_NUMBER;
  const format = formatOf(name);
  if (format.duration) return formatDuration(value);
  const number = formatNumber(value, format.decimals, roundingOf(name));
  if (unit === "") return number;
  return unit === "%" ? `${number}%` : `${number} ${unit}`;
}

/** One value as a row: label, text and the look of its level. */
export function valueRow(state: State | null, name: string, conn: Conn): ValueRow {
  const { value, unit, level } = readValue(state, name, conn);
  return { name, label: formatOf(name).label, text: valueText(name, value, unit), ...lookOf(level) };
}
