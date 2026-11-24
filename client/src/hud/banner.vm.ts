// The alert banner: up to three alerts, in the order the backend sent them, plus "+N MORE".
// The backend decides severity and order (unacknowledged first); this only picks the look.
import type { Alert, Level, State } from "../contract.gen";
import { theme } from "../theme";
import type { BannerRow, BannerVm, Conn } from "./types";
import { lookOf } from "./values";

export const BANNER_ROWS = 3;

/** Severity to level. A severity this client does not know (a newer backend) is a warning. */
function levelOf(severity: unknown): Level {
  return severity === "caution" ? "caution" : "warning";
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function bannerVm(state: State | null, conn: Conn): BannerVm {
  const alerts: readonly Alert[] = Array.isArray(state?.alerts) ? state.alerts : [];
  // Alerts from a backend we no longer hear may be over: they stay listed, in the stale look.
  const live = conn === "live";
  const rows: BannerRow[] = alerts.slice(0, BANNER_ROWS).map((alert) => ({
    id: text(alert.id),
    title: text(alert.title),
    action: text(alert.action),
    acked: alert.acked === true,
    ackText: alert.acked === true ? "ACK" : "",
    actionColor: alert.acked === true ? theme.color.label : theme.color.text,
    ...lookOf(live ? levelOf(alert.severity) : "stale"),
  }));
  const more = Math.max(0, alerts.length - BANNER_ROWS);
  return {
    rows,
    more,
    moreText: more > 0 ? `+${more} MORE` : null,
    topId: rows[0]?.id || null,
    visible: rows.length > 0,
  };
}
