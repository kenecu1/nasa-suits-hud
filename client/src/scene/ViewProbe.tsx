// Measures what was really drawn, once per frame, for window.__hud.view: is the panel inside
// the view of each eye, where the head and the rig point, and how many draw calls a frame took.
// It reads the renderer's own cameras, so in a WebXR session it sees what the headset sees.
import { useFrame, type RootState } from "@react-three/fiber";
import { useXR } from "@react-three/xr";
import { useRef, type RefObject } from "react";
import { Vector3, type Camera, type Group } from "three";
import type { HudView } from "../testHook";
import { theme } from "../theme";
import { RIG_PLACED } from "./HudRig";
import { headYaw } from "./rigMath";

const RAD_TO_DEG = 180 / Math.PI;
const halfW = (theme.panel.width * theme.panel.pixelSize) / 2;
const halfH = (theme.panel.height * theme.panel.pixelSize) / 2;
const CORNERS = [
  [-halfW, -halfH],
  [halfW, -halfH],
  [halfW, halfH],
  [-halfW, halfH],
] as const;

const point = new Vector3();
const direction = new Vector3();

/** True when a world point lies inside what this camera draws. */
function sees(eye: Camera, world: Vector3): boolean {
  point.copy(world).applyMatrix4(eye.matrixWorldInverse).applyMatrix4(eye.projectionMatrix);
  return Math.abs(point.x) <= 1 && Math.abs(point.y) <= 1 && Math.abs(point.z) <= 1;
}

export function ViewProbe({ rigRef, panelRef }: {
  rigRef: RefObject<Group | null>;
  panelRef: RefObject<Group | null>;
}) {
  const xrMode = useXR((s) => s.mode);
  const corner = useRef(new Vector3());
  const view = useRef<HudView>({
    frames: 0,
    drawCalls: 0,
    maxDrawCalls: 0,
    presenting: false,
    xrMode: null,
    panelInView: false,
    framesOutOfView: 0,
    headYawDeg: 0,
    rigYawDeg: 0,
  });

  const broken = useRef(false);

  // This runs before the frame is drawn, so the numbers describe the frame before it.
  useFrame((frame) => {
    if (broken.current) return;
    try {
      measure(frame);
    } catch (error) {
      // Measuring is for tests. It must never stop the frame loop that draws the HUD.
      broken.current = true;
      console.error("The view probe stopped", error);
    }
  });

  function measure({ gl, camera }: RootState): void {
    const rig = rigRef.current;
    const panel = panelRef.current;
    if (rig === null || panel === null || rig.userData[RIG_PLACED] !== true) return;

    const v = view.current;
    const presenting = gl.xr.isPresenting;
    const eyes: readonly Camera[] = presenting ? gl.xr.getCamera().cameras : [camera];

    panel.updateWorldMatrix(true, false);
    let inView = eyes.length > 0;
    for (const [x, y] of CORNERS) {
      corner.current.set(x, y, 0).applyMatrix4(panel.matrixWorld);
      for (const eye of eyes) inView &&= sees(eye, corner.current);
    }

    camera.getWorldDirection(direction);
    v.frames += 1;
    v.drawCalls = gl.info.render.calls;
    v.maxDrawCalls = Math.max(v.maxDrawCalls, v.drawCalls);
    v.presenting = presenting;
    v.xrMode = xrMode;
    v.panelInView = inView;
    if (!inView) v.framesOutOfView += 1;
    v.headYawDeg = headYaw(direction.x, direction.z, v.headYawDeg / RAD_TO_DEG) * RAD_TO_DEG;
    v.rigYawDeg = rig.rotation.y * RAD_TO_DEG;
    window.__hud.view = v;
  }

  return null;
}
