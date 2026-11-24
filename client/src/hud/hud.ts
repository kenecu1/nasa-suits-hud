// All view models for one state. The components draw exactly this, and tests read it on
// window.__hud.panels. `prev` is the state before this one (used by the tone only).
import type { State } from "../contract.gen";
import { bannerVm } from "./banner.vm";
import { clockVm } from "./clock.vm";
import { consumablesVm } from "./consumables.vm";
import { detailsVm } from "./details.vm";
import { linkVm } from "./link.vm";
import { switchesVm } from "./switches.vm";
import { toneVm } from "./tone.vm";
import type { Conn, HudPanels } from "./types";
import { vitalsVm } from "./vitals.vm";

export function buildHud(state: State | null, conn: Conn, prev: State | null = null): HudPanels {
  return {
    banner: bannerVm(state, conn),
    tone: toneVm(state, prev, conn),
    consumables: consumablesVm(state, conn),
    vitals: vitalsVm(state, conn),
    switches: switchesVm(state, conn),
    details: detailsVm(state, conn),
    clock: clockVm(state, conn),
    link: linkVm(state, conn),
  };
}
