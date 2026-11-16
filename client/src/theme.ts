// Every size and colour the HUD uses. Components and view models take them from here
// (CLAUDE.md: no literal colours or font sizes in components). Plain data: no three.js, no React.
import type { Level } from "./contract.gen";

/** The outline drawn next to a value. Each level has its own, so colour is never the only cue. */
export type Shape = "circle" | "diamond" | "triangle" | "ring" | "square";

export interface LevelStyle {
  color: string;
  shape: Shape;
  word: string;
}

const color = {
  backdrop: "#05070a", // laptop view only; in the headset the background is the real world
  panel: "#0b1118", // dark backing (see panel.opacity), so contrast does not depend on what is behind
  text: "#e8eef5",
  label: "#9fb0c2",
  nominal: "#4ade80",
  caution: "#facc15",
  warning: "#f87171",
  unknown: "#94a3b8",
  stale: "#b8a58c",
} as const;

export const theme = {
  color,

  /** How each level looks: colour, shape and word together (architecture.md, HUD layout rules). */
  level: {
    nominal: { color: color.nominal, shape: "circle", word: "NOMINAL" },
    caution: { color: color.caution, shape: "diamond", word: "CAUTION" },
    warning: { color: color.warning, shape: "triangle", word: "WARNING" },
    unknown: { color: color.unknown, shape: "ring", word: "NO DATA" },
    stale: { color: color.stale, shape: "square", word: "STALE" },
  } satisfies Record<Level, LevelStyle>,

  /** Panel sizes in panel pixels. One panel pixel is `pixelSize` metres. */
  panel: {
    pixelSize: 0.001,
    opacity: 0.88,
    width: 340,
    height: 236,
    padding: 18,
    gap: 10,
    radius: 14,
    rowGap: 12,
    shapeSize: 30,
    smallShapeSize: 18,
  },

  font: {
    label: 18,
    value: 56,
    word: 22,
    row: 22,
  },

  /** The rig that carries the panels: it follows the head with a delay and only turns. */
  rig: {
    distanceM: 1.2,
    followS: 0.35, // time for the rig to close about 63% of the gap to the head's direction
    panelYawDeg: -15, // negative = to the wearer's right
    panelPitchDeg: -11, // negative = below eye level; the centre of view stays clear
  },

  /** Laptop view: a fixed camera at standing eye height. */
  camera: {
    fovDeg: 50,
    eyeHeightM: 1.6,
    near: 0.05,
    far: 50,
  },
} as const;

export const LEVELS: readonly Level[] = ["nominal", "caution", "warning", "unknown", "stale"];
