// window.__hud: what the HUD is showing, for end-to-end tests. HUD content is drawn in WebGL
// and is not in the DOM, so tests read the same view models the components draw.
import type { HudPanels, Conn } from "./hud/types";
import { useHud } from "./store";

/** Measured from the real renderer and camera once per frame (scene/ViewProbe.tsx). */
export interface HudView {
  /** Frames drawn so far. */
  frames: number;
  /** Draw calls of the last frame, and the most seen in any frame (renderer.info). */
  drawCalls: number;
  maxDrawCalls: number;
  /** True when a WebXR session is presenting, and its mode ("immersive-ar"). */
  presenting: boolean;
  xrMode: string | null;
  /** All four corners of the panel are inside the view of every eye. */
  panelInView: boolean;
  /** Frames in which the panel was not fully in view. */
  framesOutOfView: number;
  /** Where the head and the rig point, degrees about the up axis (positive = left). */
  headYawDeg: number;
  rigYawDeg: number;
}

export interface HudHook {
  panels: HudPanels;
  conn: Conn;
  /** `seq` of the last state received, null before the first. */
  seq: number | null;
  /** null until the scene has drawn a frame. */
  view: HudView | null;
}

declare global {
  interface Window {
    __hud: HudHook;
  }
}

export function installTestHook(): () => void {
  const read = (): Omit<HudHook, "view"> => {
    const { panels, conn, state } = useHud.getState();
    return { panels, conn, seq: state?.seq ?? null };
  };
  window.__hud = { ...read(), view: null };
  return useHud.subscribe(() => Object.assign(window.__hud, read()));
}
