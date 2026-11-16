// The DCU oxygen switch position. Pure function, no drawing.
import type { State } from "../contract.gen";
import { theme } from "../theme";
import type { Conn, DcuVm } from "./types";

export function dcuVm(state: State | null, conn: Conn): DcuVm {
  const position = state?.dcu?.oxy ?? null;
  const current = position !== null && conn === "live";

  let color: string = theme.color.text;
  if (position === null) color = theme.level.unknown.color;
  else if (!current) color = theme.level.stale.color;

  return { label: "O2 SWITCH", text: position ?? "--", current, color };
}
