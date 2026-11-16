// Primary oxygen: what the panel says and how it looks. Pure function, no drawing.
import type { Level, State } from "../contract.gen";
import { theme } from "../theme";
import type { Conn, O2Vm } from "./types";

const NAME = "oxy_pri_storage";
const NO_NUMBER = "--";

function isLevel(value: unknown): value is Level {
  return typeof value === "string" && Object.hasOwn(theme.level, value);
}

export function o2Vm(state: State | null, conn: Conn): O2Vm {
  const reading = state?.suit.values[NAME];
  const value = reading?.value;
  // A number is shown only with a level this client knows how to draw. Anything else (no value,
  // not a finite number, a level word from a newer backend) is "no data", never a bare number.
  const usable = typeof value === "number" && Number.isFinite(value) && isLevel(reading?.level);

  // The backend decides the level. The client only overrides it when it cannot trust what it
  // holds: nothing usable means unknown, and a number from a backend we no longer hear is stale.
  let level: Level = "unknown";
  if (usable) level = conn === "live" ? (reading?.level ?? "unknown") : "stale";

  const unit = typeof reading?.unit === "string" ? reading.unit : "";
  return {
    label: "O2 PRI",
    // Floored, not rounded: 19.6 must not read "20%" when 20 is the limit.
    text: usable ? `${Math.floor(value)}${unit}` : NO_NUMBER,
    level,
    ...theme.level[level],
  };
}
