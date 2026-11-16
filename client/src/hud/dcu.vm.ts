// The DCU oxygen switch position. Pure function, no drawing.
import type { State } from "../contract.gen";
import { theme } from "../theme";
import type { Conn, DcuVm } from "./types";

const POSITIONS: readonly string[] = ["PRI", "SEC"];

export function dcuVm(state: State | null, conn: Conn): DcuVm {
  const raw: unknown = state?.dcu?.oxy;
  // Only the two positions the contract names. Anything else is shown as unknown, not passed on.
  const position = typeof raw === "string" && POSITIONS.includes(raw) ? raw : null;
  const current = position !== null && conn === "live";

  let color: string = theme.color.text;
  if (position === null) color = theme.level.unknown.color;
  else if (!current) color = theme.level.stale.color;

  return { label: "O2 SWITCH", text: position ?? "--", current, color };
}
