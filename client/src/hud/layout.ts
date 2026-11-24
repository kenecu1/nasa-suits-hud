// Where each panel sits, in degrees around the wearer, and how big it is in panel pixels.
// The rig places the panels from this table (scene/HudRig.tsx), the view probe checks their
// corners from it (scene/ViewProbe.tsx), and layout.test.ts checks that none covers the centre
// of view (acceptance 8). Pure data and maths: no three.js.
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

const SIDE_YAW = 27.2;
const SIDE_WIDTH = 500;

export const LAYOUT: Readonly<Record<PanelName, PanelBox>> = {
  banner: { yawDeg: 0, pitchDeg: 24, anchor: "top", widthPx: 640, heightPx: 270 },
  status: { yawDeg: SIDE_YAW, pitchDeg: 18.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 110 },
  vitals: { yawDeg: SIDE_YAW, pitchDeg: 4, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 200 },
  switches: { yawDeg: SIDE_YAW, pitchDeg: -17.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 270 },
  consumables: { yawDeg: -SIDE_YAW, pitchDeg: -17.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 270 },
  detailsLeft: { yawDeg: SIDE_YAW, pitchDeg: -7.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 580 },
  detailsRight: { yawDeg: -SIDE_YAW, pitchDeg: -2.5, anchor: "center", widthPx: SIDE_WIDTH, heightPx: 520 },
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

const DEG = 180 / Math.PI;

/** Angle a length takes up when seen square-on at the panel distance. */
function angleOf(lengthPx: number): number {
  return Math.atan((lengthPx * theme.panel.pixelSize) / theme.rig.distanceM) * DEG;
}

export function angleBox(box: PanelBox): AngleBox {
  const halfW = angleOf(box.widthPx / 2);
  const top = box.anchor === "top" ? box.pitchDeg : box.pitchDeg + angleOf(box.heightPx / 2);
  const bottom = box.anchor === "top" ? box.pitchDeg - angleOf(box.heightPx) : box.pitchDeg - angleOf(box.heightPx / 2);
  return { left: box.yawDeg + halfW, right: box.yawDeg - halfW, top, bottom };
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

/** What both the laptop camera and an emulated headset eye can see. */
export const VIEW_LIMIT: AngleBox = {
  left: theme.view.maxYawDeg,
  right: -theme.view.maxYawDeg,
  top: theme.view.maxPitchDeg,
  bottom: -theme.view.maxPitchDeg,
};

export function inside(inner: AngleBox, outer: AngleBox): boolean {
  return inner.left <= outer.left && inner.right >= outer.right && inner.top <= outer.top && inner.bottom >= outer.bottom;
}
