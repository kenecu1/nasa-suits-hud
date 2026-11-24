// The link line: is the HUD hearing the backend, and is the backend hearing the TSS?
// The backend decides how serious its link status is (`link.level`). The only look chosen here
// is for the client's own connection: only the client knows its socket is down.
import type { LinkStatus, State } from "../contract.gen";
import type { Conn, LinkVm } from "./types";
import { isLevel, lookOf } from "./values";

const TEXT: Record<LinkStatus, string> = {
  ok: "TSS OK",
  stale: "TSS STALE",
  unreachable: "TSS UNREACHABLE",
  unassigned: "TSS NOT ASSIGNED",
  bad_data: "TSS BAD DATA",
};

export function linkVm(state: State | null, conn: Conn): LinkVm {
  const mode = state ? String(state.link.mode).toUpperCase() : null;
  // The client's own connection comes first: what the backend last said about the TSS is
  // worth nothing once the backend itself is gone.
  if (conn === "offline") return { label: "LINK", text: "OFFLINE", status: "offline", mode, ...lookOf("warning") };
  if (conn === "connecting" || state === null) {
    return { label: "LINK", text: "CONNECTING", status: "connecting", mode, ...lookOf("unknown") };
  }
  const status = state.link.tss;
  const text = Object.hasOwn(TEXT, status) ? TEXT[status] : `TSS ${String(status).toUpperCase()}`;
  // A level this client does not know (a newer backend) is a warning, never shown as fine.
  const level = isLevel(state.link.level) ? state.link.level : "warning";
  return { label: "LINK", text, status, mode, ...lookOf(level) };
}
