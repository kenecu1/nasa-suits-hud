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
  input: InputLog;
  receive: (state: State) => void;
  setConn: (conn: Conn) => void;
  noteIntent: (record: IntentRecord) => void;
}

export const useHud = create<HudStore>((set) => ({
  state: null,
  prev: null,
  conn: "connecting",
  panels: buildHud(null, "connecting"),
  input: { last: null, count: 0, dropped: 0 },
  receive: (state) => set((s) => ({ state, prev: s.state, panels: buildHud(state, s.conn, s.state) })),
  setConn: (conn) => set((s) => ({ conn, panels: buildHud(s.state, conn, s.prev) })),
  noteIntent: (record) =>
    set((s) => ({
      input: { last: record, count: s.input.count + 1, dropped: s.input.dropped + (record.sent ? 0 : 1) },
    })),
}));
