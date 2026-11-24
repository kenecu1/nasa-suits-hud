// The EVA clock, top left.
import type { State } from "../contract.gen";
import { theme } from "../theme";
import type { ClockVm, Conn } from "./types";
import { formatDuration } from "./values";

export function clockVm(state: State | null, conn: Conn): ClockVm {
  const color = conn === "live" ? theme.color.text : theme.level.stale.color;
  const eva = state?.eva;
  if (eva?.started === false) return { label: "EVA", text: "NOT STARTED", color };
  const elapsed = eva?.elapsed_s;
  if (typeof elapsed !== "number" || !Number.isFinite(elapsed)) {
    return { label: "EVA", text: "--:--:--", color: theme.level.unknown.color };
  }
  return { label: "EVA", text: formatDuration(elapsed), color };
}
