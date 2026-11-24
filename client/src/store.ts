// The client's whole state: the last State from the backend (and the one before it, for the
// tone), whether the link is alive, the view models built from them, and the last intent.
// The backend's message replaces what was there.
import { create } from "zustand";
import type { State } from "./contract.gen";
import { buildHud } from "./hud/hud";
import type { Conn, HudPanels } from "./hud/types";
import type { IntentRecord } from "./input/dispatch";

export interface InputLog {
  /** The last intent and what became of it; null before the first. */
  last: IntentRecord | null;
  /** Intents fired, and how many of them the link dropped. */
  count: number;
  dropped: number;
}

export interface HudStore {
  state: State | null;
  prev: State | null;
  conn: Conn;
  /** Always buildHud(state, conn, prev): rebuilt whenever one changes. */
  panels: HudPanels;
  /** How many warning tones are due since the page loaded: +1 for each state whose tone says play. */
  toneCount: number;
  /** The tone key last counted, so a rebuild for the same state does not count it twice. */
  toneKey: string | null;
  input: InputLog;
  receive: (state: State) => void;
  setConn: (conn: Conn) => void;
  noteIntent: (record: IntentRecord) => void;
}

type Built = Pick<HudStore, "panels" | "toneCount" | "toneKey">;

function build(s: HudStore, state: State | null, conn: Conn, prev: State | null): Built {
  const panels = buildHud(state, conn, prev);
  const due = panels.tone.play && panels.tone.key !== s.toneKey;
  return { panels, toneCount: s.toneCount + (due ? 1 : 0), toneKey: due ? panels.tone.key : s.toneKey };
}

export const useHud = create<HudStore>((set) => ({
  state: null,
  prev: null,
  conn: "connecting",
  panels: buildHud(null, "connecting"),
  toneCount: 0,
  toneKey: null,
  input: { last: null, count: 0, dropped: 0 },
  receive: (state) => set((s) => ({ state, prev: s.state, ...build(s, state, s.conn, s.state) })),
  setConn: (conn) => set((s) => ({ conn, ...build(s, s.state, conn, s.prev) })),
  noteIntent: (record) =>
    set((s) => ({
      input: { last: record, count: s.input.count + 1, dropped: s.input.dropped + (record.sent ? 0 : 1) },
    })),
}));
