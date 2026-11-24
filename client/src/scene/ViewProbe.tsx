// Measures what the renderer really draws, once a frame, into window.__hud.view: draw calls,
// whether a WebXR session is presenting, and whether every panel shown is fully in view of
// every eye. End-to-end tests read it, because nothing inside the HUD is in the DOM.
import { useFrame, type RootState } from "@react-three/fiber";
import { useXR } from "@react-three/xr";
import { useRef, type RefObject } from "react";
import { Vector3, type Camera, type Group } from "three";
import { LAYOUT, localCorners, type PanelName } from "../hud/layout";
import type { HudView } from "../testHook";
import { RIG_PLACED } from "./HudRig";
import type { PanelRegistry } from "./PanelAt";
import { headYaw } from "./rigMath";

const RAD_TO_DEG = 180 / Math.PI;
const point = new Vector3();
const corner = new Vector3();
const direction = new Vector3();
const laptopEye: Camera[] = [];

const CORNERS = Object.fromEntries((Object.keys(LAYOUT) as PanelName[]).map((n) => [n, localCorners(LAYOUT[n])])) as Record<
  PanelName,
  [number, number][]
>;

/** True when a world point lies inside what this camera draws. */
function sees(eye: Camera, world: Vector3): boolean {
  point.copy(world).applyMatrix4(eye.matrixWorldInverse).applyMatrix4(eye.projectionMatrix);
  return Math.abs(point.x) <= 1 && Math.abs(point.y) <= 1 && Math.abs(point.z) <= 1;
}

export function ViewProbe({ rigRef, registry }: { rigRef: RefObject<Group | null>; registry: PanelRegistry }) {
  const xrMode = useXR((s) => s.mode);
  const view = useRef<HudView>({
    frames: 0,
    drawCalls: 0,
    maxDrawCalls: 0,
    presenting: false,
    xrMode: null,
    panelsShown: [],
    panelInView: false,
    panelsOutOfView: [],
    framesOutOfView: 0,
    headYawDeg: 0,
    rigYawDeg: 0,
    probeError: null,
  });
  const broken = useRef(false);

  useFrame((frame) => {
    if (broken.current) return;
    try {
      measure(frame);
    } catch (error) {
      broken.current = true;
      console.error("The view probe stopped", error);
      // Never leave the last good reading standing: a test must see that measuring stopped.
      const v = view.current;
      v.panelInView = false;
      v.probeError = error instanceof Error ? error.message : String(error);
      if (window.__hud) window.__hud.view = v;
    }
  });

  function measure({ gl, camera }: RootState): void {
    const rig = rigRef.current;
    if (rig === null || rig.userData[RIG_PLACED] !== true) return;
    const v = view.current;
    const presenting = gl.xr.isPresenting;
    laptopEye[0] = camera;
    const eyes: readonly Camera[] = presenting ? gl.xr.getCamera().cameras : laptopEye;

    const shown: PanelName[] = [];
    const outOfView: PanelName[] = [];
    for (const [name, group] of registry) {
      shown.push(name);
      group.updateWorldMatrix(true, false);
      let inView = eyes.length > 0;
      for (const [x, y] of CORNERS[name]) {
        corner.set(x, y, 0).applyMatrix4(group.matrixWorld);
        for (let e = 0; e < eyes.length; e++) inView &&= sees(eyes[e] as Camera, corner);
      }
      if (!inView) outOfView.push(name);
    }

    camera.getWorldDirection(direction);
    v.frames += 1;
    v.drawCalls = gl.info.render.calls;
    v.maxDrawCalls = Math.max(v.maxDrawCalls, v.drawCalls);
    v.presenting = presenting;
    v.xrMode = xrMode;
    v.panelsShown = shown.sort();
    v.panelsOutOfView = outOfView.sort();
    v.panelInView = shown.length > 0 && outOfView.length === 0;
    if (!v.panelInView) v.framesOutOfView += 1;
    v.headYawDeg = headYaw(direction.x, direction.z, v.headYawDeg / RAD_TO_DEG) * RAD_TO_DEG;
    v.rigYawDeg = rig.rotation.y * RAD_TO_DEG;
    if (window.__hud) window.__hud.view = v;
  }

  return null;
}
