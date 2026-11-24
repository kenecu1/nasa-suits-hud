// The warning tone: play once when a warning appears that was not a warning in the previous
// state (a new alert, or a caution that became a warning). Acknowledged warnings never play.
import type { State } from "../contract.gen";
import type { Conn, ToneVm } from "./types";

function warningIds(state: State | null, unackedOnly: boolean): Set<string> {
  const alerts = Array.isArray(state?.alerts) ? state.alerts : [];
  return new Set(
    alerts.filter((a) => a.severity !== "caution" && (!unackedOnly || a.acked !== true)).map((a) => String(a.id)),
  );
}

export function toneVm(state: State | null, prev: State | null, conn: Conn): ToneVm {
  const key = state === null ? "none" : `${state.seq}@${state.t}`;
  if (conn !== "live" || state === null) return { play: false, key, newWarnings: [] };
  const before = warningIds(prev, false);
  const newWarnings = [...warningIds(state, true)].filter((id) => !before.has(id)).sort();
  return { play: newWarnings.length > 0, key, newWarnings };
}
