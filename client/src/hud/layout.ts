// Where each panel sits, in degrees around the wearer, and how big it is in panel pixels.
// The rig places the panels from this table (scene/PanelAt.tsx), the view probe checks their
// corners from it (scene/ViewProbe.tsx), and layout.test.ts checks that none covers the centre
// of view (acceptance 8) and that each fits every picture. Pure data and maths: no three.js.
import { theme } from "../theme";

export type PanelName =
  | "banner"
  | "status"
  | "vitals"
  | "switches"
  | "consumables"
  | "detailsLeft"
  | "detailsRight";

export interface PanelBox {
  /** Direction of the panel's anchor point. Yaw positive = to the wearer's left; pitch positive = up. */
  yawDeg: number;
  pitchDeg: number;
  /** The anchor point is the centre of the panel, or the middle of its top edge. */
  anchor: "center" | "top";
  /** The largest the panel can be. A panel that grows with its content (the banner) stays inside. */
  widthPx: number;
  heightPx: number;
}

const SIDE_YAW = 27.5;
const SIDE_WIDTH = 470;

export const LAYOUT: Readonly<Record<PanelName, PanelBox>> = {
  banner: { yawDeg: 0, pitchDeg: 24.5, anchor: "top", widthPx: 600, heightPx: 300 },
  status: { yawDeg: SIDE_YAW, pitchDeg: 19.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 120 },
  vitals: { yawDeg: SIDE_YAW, pitchDeg: 4, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 210 },
  switches: { yawDeg: SIDE_YAW, pitchDeg: -18.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 340 },
  consumables: { yawDeg: -SIDE_YAW, pitchDeg: -18.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 340 },
  detailsLeft: { yawDeg: SIDE_YAW, pitchDeg: -12, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 650 },
  detailsRight: { yawDeg: -SIDE_YAW, pitchDeg: -6, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 580 },
};

/** Panels on screen while the details page is closed, and while it is open (it replaces three). */
export const PANELS_DETAILS_CLOSED: readonly PanelName[] = ["banner", "status", "vitals", "switches", "consumables"];
export const PANELS_DETAILS_OPEN: readonly PanelName[] = ["banner", "status", "detailsLeft", "detailsRight"];

/** A panel's extent in degrees. `left` > `right` because yaw grows to the left. */
export interface AngleBox {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

const DEG = Math.PI / 180;

/** A point in the rig's frame, metres: x right, y up, the wearer looks down -z. */
export type Point = [number, number, number];

/**
 * The panel's four corners in the rig's frame, placed exactly as scene/PanelAt.tsx places them:
 * turned by yaw, tilted by pitch, then pushed out to the panel distance.
 */
export function cornerPoints(box: PanelBox): Point[] {
  const w = (box.widthPx * theme.panel.pixelSize) / 2;
  const h = box.heightPx * theme.panel.pixelSize;
  const [top, bottom] = box.anchor === "top" ? [0, -h] : [h / 2, -h / 2];
  const pitch = box.pitchDeg * DEG;
  const yaw = box.yawDeg * DEG;
  const z0 = -theme.rig.distanceM;
  const flat: [number, number][] = [
    [-w, bottom],
    [w, bottom],
    [w, top],
    [-w, top],
  ];
  return flat.map(([x, y]): Point => {
    const y1 = y * Math.cos(pitch) - z0 * Math.sin(pitch);
    const z1 = y * Math.sin(pitch) + z0 * Math.cos(pitch);
    return [x * Math.cos(yaw) + z1 * Math.sin(yaw), y1, -x * Math.sin(yaw) + z1 * Math.cos(yaw)];
  });
}

/** Yaw (positive = left) and pitch (positive = up) of a point seen from the rig's centre, degrees. */
function anglesOf([x, y, z]: Point): [number, number] {
  return [Math.atan2(-x, -z) / DEG, Math.atan2(y, Math.hypot(x, z)) / DEG];
}

/** The smallest box of directions that holds the whole panel (its corners are its extremes). */
export function angleBox(box: PanelBox): AngleBox {
  const angles = cornerPoints(box).map(anglesOf);
  const yaws = angles.map((a) => a[0]);
  const pitches = angles.map((a) => a[1]);
  return { left: Math.max(...yaws), right: Math.min(...yaws), top: Math.max(...pitches), bottom: Math.min(...pitches) };
}

/** True when the two boxes share any area (touching edges do not count). */
export function overlaps(a: AngleBox, b: AngleBox): boolean {
  return a.right < b.left && b.right < a.left && a.bottom < b.top && b.bottom < a.top;
}

/** The centre of view that must stay clear: 30° wide and 20° tall (acceptance 8). */
export const CLEAR_ZONE: AngleBox = {
  left: theme.view.clearYawDeg,
  right: -theme.view.clearYawDeg,
  top: theme.view.clearPitchDeg,
  bottom: -theme.view.clearPitchDeg,
};

/** A flat camera looking down -z from `eyeX` metres to the side, by the tangents of its half-angles. */
export interface Eye {
  name: string;
  eyeX: number;
  tanX: number;
  tanY: number;
}

const tan = (deg: number): number => Math.tan(deg * DEG);
const { view, camera } = theme;

/** The laptop camera (1280 x 720 in the end-to-end tests) and the two emulated Quest 3 eyes. */
export const EYES: readonly Eye[] = [
  { name: "laptop", eyeX: 0, tanX: tan(camera.fovDeg / 2) * view.laptopAspect, tanY: tan(camera.fovDeg / 2) },
  { name: "left eye", eyeX: -view.eyeOffsetM, tanX: view.eyeTanX, tanY: view.eyeTanY },
  { name: "right eye", eyeX: view.eyeOffsetM, tanX: view.eyeTanX, tanY: view.eyeTanY },
];

/** How far out the panel reaches in this eye's picture: 1 is the edge, above 1 is cut off. */
export function reach(box: PanelBox, eye: Eye): number {
  const out = cornerPoints(box).map(([x, y, z]) =>
    Math.max(Math.abs((x - eye.eyeX) / -z) / eye.tanX, Math.abs(y / -z) / eye.tanY),
  );
  return Math.max(...out);
}
