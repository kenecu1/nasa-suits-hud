// The link line: is the HUD hearing the backend, and is the backend hearing the TSS?
import type { Level, LinkStatus, State } from "../contract.gen";
import { theme } from "../theme";
import type { Conn, LinkVm } from "./types";

const TSS: Record<LinkStatus, { text: string; level: Level }> = {
  ok: { text: "TSS OK", level: "nominal" },
  stale: { text: "TSS STALE", level: "stale" },
  unreachable: { text: "TSS UNREACHABLE", level: "warning" },
  unassigned: { text: "TSS NOT ASSIGNED", level: "warning" },
  bad_data: { text: "TSS BAD DATA", level: "warning" },
};

export function linkVm(state: State | null, conn: Conn): LinkVm {
  const mode = state ? state.link.mode.toUpperCase() : null;

  // The client's own connection comes first: what the backend last said about the TSS is
  // worth nothing once the backend itself is gone.
  if (conn === "offline") return look("offline", "OFFLINE", "warning", mode);
  if (conn === "connecting" || state === null) return look("connecting", "CONNECTING", "unknown", mode);

  const status = state.link.tss;
  const known = TSS[status] as { text: string; level: Level } | undefined;
  // A status this client does not know (a newer backend) is a warning, never shown as fine.
  if (known === undefined) return look(status, `TSS ${String(status).toUpperCase()}`, "warning", mode);
  return look(status, known.text, known.level, mode);
}

function look(status: LinkVm["status"], text: string, level: Level, mode: string | null): LinkVm {
  return { label: "LINK", text, status, mode, level, ...theme.level[level] };
}
