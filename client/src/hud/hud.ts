// All view models for one state. The components draw exactly this, and tests read it on
// window.__hud.panels.
import type { State } from "../contract.gen";
import { dcuVm } from "./dcu.vm";
import { linkVm } from "./link.vm";
import { o2Vm } from "./o2.vm";
import type { Conn, HudPanels } from "./types";

export function buildHud(state: State | null, conn: Conn): HudPanels {
  return {
    o2: o2Vm(state, conn),
    dcu: dcuVm(state, conn),
    link: linkVm(state, conn),
  };
}
