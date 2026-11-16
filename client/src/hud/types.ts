// What the view models hand to the components, and what tests read on window.__hud.
import type { Level, LinkStatus } from "../contract.gen";
import type { Shape } from "../theme";

/**
 * The client's own view of its connection to the backend.
 * connecting: no message yet since the page loaded. live: a state message arrived in the last
 * 3 s. offline: the socket closed, or nothing understandable arrived for 3 s.
 */
export type Conn = "connecting" | "live" | "offline";

/** How a level is drawn. Always all three together: colour, shape and word. */
export interface LevelLook {
  level: Level;
  color: string;
  shape: Shape;
  word: string;
}

export interface O2Vm extends LevelLook {
  label: string;
  /** "92%", or "--" when there is no number to show. */
  text: string;
}

export interface DcuVm {
  label: string;
  /** The named switch position ("PRI" or "SEC"), or "--" when unknown. */
  text: string;
  /** False when the position is unknown or may be out of date (no DCU data, or not live). */
  current: boolean;
  color: string;
}

export interface LinkVm extends LevelLook {
  label: string;
  /** What the link line says, e.g. "TSS OK", "OFFLINE". */
  text: string;
  /** "offline" and "connecting" are the client's own; the rest is the backend's link.tss. */
  status: "connecting" | "offline" | LinkStatus;
  /** "SIM", "REPLAY" or "LIVE"; null until the backend has said. */
  mode: string | null;
}

export interface HudPanels {
  o2: O2Vm;
  dcu: DcuVm;
  link: LinkVm;
}
