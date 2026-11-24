// window.__hud: what the HUD is showing, for end-to-end tests. HUD content is drawn in WebGL
// and is not in the DOM, so tests read the same view models the components draw.
import type { HudPanels, Conn } from "./hud/types";
import type { PanelName } from "./hud/layout";
import { useHud, type InputLog } from "./store";

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
  /** The panels drawn in the last frame. */
  panelsShown: PanelName[];
  /** All four corners of every panel shown are inside the view of every eye. */
  panelInView: boolean;
  /** The panels shown with a corner outside some eye's view in the last frame. */
  panelsOutOfView: PanelName[];
  /** Frames in which some panel was not fully in view. */
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
  /** The last intent fired (keyboard or controller) and what the link did with it. */
  input: InputLog;
  /** How many times the warning tone has played. */
  tones: number;
  /** null until the scene has drawn a frame. */
  view: HudView | null;
}

declare global {
  interface Window {
    __hud: HudHook;
  }
}

export function installTestHook(): () => void {
  const read = (): Omit<HudHook, "view" | "tones"> => {
    const { panels, conn, state, input } = useHud.getState();
    return { panels, conn, input, seq: typeof state?.seq === "number" ? state.seq : null };
  };
  window.__hud = { ...read(), tones: 0, view: null };
  return useHud.subscribe(() => Object.assign(window.__hud, read()));
}
