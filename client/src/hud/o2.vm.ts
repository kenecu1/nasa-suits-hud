// Primary oxygen: what the panel says and how it looks. Pure function, no drawing.
import type { Level, State } from "../contract.gen";
import { theme } from "../theme";
import type { Conn, O2Vm } from "./types";

const NAME = "oxy_pri_storage";
const NO_NUMBER = "--";

export function o2Vm(state: State | null, conn: Conn): O2Vm {
  const reading = state?.suit.values[NAME];
  const value = reading?.value;
  const hasNumber = typeof value === "number" && Number.isFinite(value);

  // The backend decides the level. The client only overrides it when it cannot trust what it
  // holds: no number means unknown, and a number from a backend we no longer hear is stale.
  let level: Level;
  if (!hasNumber) level = "unknown";
  else if (conn !== "live") level = "stale";
  else level = reading?.level ?? "unknown";

  return {
    label: "O2 PRI",
    // Floored, not rounded: 19.6 must not read "20%" when 20 is the limit.
    text: hasNumber ? `${Math.floor(value)}${reading?.unit ?? ""}` : NO_NUMBER,
    level,
    ...theme.level[level],
  };
}
