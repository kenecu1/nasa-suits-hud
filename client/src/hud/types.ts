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

/** One alert row of the banner. */
export interface BannerRow extends LevelLook {
  id: string;
  title: string;
  action: string;
  /** The wearer has acknowledged it (the backend says so). It stays listed until it clears. */
  acked: boolean;
  /** "ACK" once acknowledged, else "". */
  ackText: string;
  /** The action line is dimmed once acknowledged. */
  actionColor: string;
}

export interface BannerVm {
  /** At most three rows, in the backend's order (unacknowledged first). */
  rows: BannerRow[];
  /** How many alerts did not fit, and the text for them ("+2 MORE"), null when none. */
  more: number;
  moreText: string | null;
  /** The id shown on the top row: what ack_alert acknowledges (decision B). */
  topId: string | null;
  /** False when there is nothing to show: the banner is not drawn. */
  visible: boolean;
}

/** Play the warning tone once per `key` when `play` is true. */
export interface ToneVm {
  play: boolean;
  /** Changes with every state that brings a new warning, so a rebuild for the same state does not replay. */
  key: string;
  /** The warning ids that were not warnings in the previous state. */
  newWarnings: string[];
}

/** One value with its look: a consumables bar, a vital or a details row. */
export interface ValueRow extends LevelLook {
  /** The telemetry name in the contract (`state.suit.values`). */
  name: string;
  label: string;
  /** "92%", "3.95 psi", or "--" when there is no number. */
  text: string;
  /**
   * The word drawn beside the value: the level's word, or "" while nominal. Seven green
   * "NOMINAL"s would be noise in a dim helmet; the circle and colour still say it.
   */
  wordText: string;
}

export interface BarRow extends ValueRow {
  /** How full the bar is, 0..1 (0 without a number). */
  fill: number;
  /** Where the warning limit mark sits, 0..1, from data/ranges.json. Null without a limit. */
  limit: number | null;
}

export interface ConsumablesVm {
  label: string;
  rows: BarRow[];
}

export interface VitalRow extends ValueRow {
  /** Drawn larger while caution or warning. */
  grown: boolean;
}

export interface VitalsVm {
  label: string;
  rows: VitalRow[];
}

export interface SwitchRow {
  label: string;
  /** The named position ("PRI", "OPEN"), or "--" when unknown. */
  text: string;
  /** False when the position is unknown or may be out of date (no data, or not live). */
  current: boolean;
  color: string;
}

export interface SwitchesVm {
  dcu: { label: string; rows: SwitchRow[] };
  uia: { label: string; rows: SwitchRow[] };
}

export interface DetailsGroup {
  title: string;
  rows: ValueRow[];
}

export interface DetailsVm {
  /** From the backend's `ui.details_open`: the page is open when the backend says so. */
  open: boolean;
  /** Two columns, drawn left and right of the clear centre. */
  columns: [DetailsGroup[], DetailsGroup[]];
  /** Every telemetry name on the page, in page order. */
  names: string[];
}

export interface ClockVm {
  label: string;
  /** "00:21:52", or a word when there is no time ("NOT STARTED", "--:--:--"). */
  text: string;
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
  banner: BannerVm;
  tone: ToneVm;
  consumables: ConsumablesVm;
  vitals: VitalsVm;
  switches: SwitchesVm;
  details: DetailsVm;
  clock: ClockVm;
  link: LinkVm;
}
