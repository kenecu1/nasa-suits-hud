// The DCU and UIA switch positions. Pure function, no drawing.
import type { State } from "../contract.gen";
import { theme } from "../theme";
import type { Conn, SwitchRow, SwitchesVm } from "./types";

interface SwitchSpec {
  key: string;
  label: string;
  positions: readonly string[];
}

// Positions as the contract names them (DcuPositions, UiaPositions in contract.gen.ts).
const DCU: readonly SwitchSpec[] = [
  { key: "batt", label: "BATT", positions: ["UMB", "LOCAL"] },
  { key: "oxy", label: "OXY", positions: ["PRI", "SEC"] },
  { key: "comm", label: "COMM", positions: ["A", "B"] },
  { key: "fan", label: "FAN", positions: ["PRI", "SEC"] },
  { key: "pump", label: "PUMP", positions: ["OPEN", "CLOSED"] },
  { key: "co2", label: "CO2", positions: ["A", "B"] },
];

const UIA: readonly SwitchSpec[] = [
  { key: "eva_power", label: "PWR", positions: ["ON", "OFF"] },
  { key: "o2_supply", label: "O2", positions: ["OPEN", "CLOSED"] },
  { key: "water_supply", label: "H2O", positions: ["OPEN", "CLOSED"] },
  { key: "water_waste", label: "WASTE", positions: ["OPEN", "CLOSED"] },
  { key: "o2_vent", label: "VENT", positions: ["OPEN", "CLOSED"] },
  { key: "depress", label: "DEPR", positions: ["OPEN", "CLOSED"] },
];

function rows(specs: readonly SwitchSpec[], source: object | null | undefined, conn: Conn): SwitchRow[] {
  return specs.map(({ key, label, positions }) => {
    const raw: unknown = source != null && Object.hasOwn(source, key) ? (source as Record<string, unknown>)[key] : null;
    // Only the positions the contract names. Anything else is shown as unknown, not passed on.
    const position = typeof raw === "string" && positions.includes(raw) ? raw : null;
    const current = position !== null && conn === "live";
    let color: string = theme.color.text;
    if (position === null) color = theme.level.unknown.color;
    else if (!current) color = theme.level.stale.color;
    return { label, text: position ?? "--", current, color };
  });
}

export function switchesVm(state: State | null, conn: Conn): SwitchesVm {
  return {
    dcu: { label: "DCU", rows: rows(DCU, state?.dcu, conn) },
    uia: { label: "UIA", rows: rows(UIA, state?.uia, conn) },
  };
}
