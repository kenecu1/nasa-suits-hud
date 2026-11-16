// The client's whole state: the last State from the backend, whether the link is alive, and
// the view models built from the two. The backend's message replaces what was there.
import { create } from "zustand";
import type { State } from "./contract.gen";
import { buildHud } from "./hud/hud";
import type { Conn, HudPanels } from "./hud/types";

export interface HudStore {
  state: State | null;
  conn: Conn;
  /** Always buildHud(state, conn): rebuilt whenever either changes. */
  panels: HudPanels;
  receive: (state: State) => void;
  setConn: (conn: Conn) => void;
}

export const useHud = create<HudStore>((set) => ({
  state: null,
  conn: "connecting",
  panels: buildHud(null, "connecting"),
  receive: (state) => set((s) => ({ state, panels: buildHud(state, s.conn) })),
  setConn: (conn) => set((s) => ({ conn, panels: buildHud(s.state, conn) })),
}));
