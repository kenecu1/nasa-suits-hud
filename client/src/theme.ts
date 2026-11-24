// Every size and colour the HUD uses. Components and view models take them from here
// (CLAUDE.md: no literal colours or font sizes in components). Plain data: no three.js, no React.
import type { Level } from "./contract.gen";

/** The outline drawn next to a value. Each level has its own, so colour is never the only cue. */
export type Shape = "circle" | "diamond" | "triangle" | "ring" | "square" | "dash";

export interface LevelStyle {
  color: string;
  shape: Shape;
  word: string;
}

/**
 * The low-light palette (decision F in docs/briefs/M2.md). Every text colour keeps at least 7:1
 * against the panel backing composited over white at `panel.opacity`: a bright lamp behind the
 * panel is the worst case. hud/contrast.test.ts checks it.
 */
const color = {
  backdrop: "#05070a", // laptop view only; in the headset the background is the real world
  panel: "#0b1118", // dark backing (see panel.opacity), so contrast does not depend on what is behind
  text: "#eef3f8",
  label: "#c3cfdb",
  nominal: "#7ee8a8",
  caution: "#fcd34d",
  warning: "#ffa8a0",
  unknown: "#c6cfd9",
  stale: "#d6c8ae",
  off: "#b4bac1", // dimmed: a device the DCU has switched off is expected to read out of range
  /** Empty part of a consumables bar. Not text, so it has no contrast rule. */
  track: "#2a3644",
} as const;

/** Distance from the eye to every panel. Sizes in dmm are angles, so they hold at any distance. */
const distanceM = 1.2;
/** One panel pixel is this many metres. */
const pixelSize = 0.001;

/** dmm (1 dmm = 1 mm seen at 1 m) to panel pixels at the panel distance. */
export function dmmToPx(dmm: number): number {
  return (dmm * distanceM) / 1000 / pixelSize;
}

/** Text sizes in dmm. Nothing smaller than `minDmm` (acceptance 6). */
const fontDmm = {
  label: 24,
  row: 24,
  word: 24,
  title: 28,
  vital: 24,
  vitalGrown: 40,
} as const;

const fontPx = Object.fromEntries(Object.entries(fontDmm).map(([k, v]) => [k, dmmToPx(v)])) as {
  [K in keyof typeof fontDmm]: number;
};

export const theme = {
  color,
  /** How each level looks: colour, shape and word together (architecture.md, HUD layout rules). */
  level: {
    nominal: { color: color.nominal, shape: "circle", word: "NOMINAL" },
    caution: { color: color.caution, shape: "diamond", word: "CAUTION" },
    warning: { color: color.warning, shape: "triangle", word: "WARNING" },
    unknown: { color: color.unknown, shape: "ring", word: "NO DATA" },
    stale: { color: color.stale, shape: "square", word: "STALE" },
    off: { color: color.off, shape: "dash", word: "OFF" },
  } satisfies Record<Level, LevelStyle>,
  /** Text sizes. `fontDmm` is the source; `font` is the same in panel pixels. */
  minDmm: 24,
  fontDmm,
  font: fontPx,
  /** Panel look, in panel pixels. */
  panel: {
    pixelSize,
    opacity: 0.92,
    padding: 14,
    gap: 10,
    radius: 14,
    rowGap: 4,
    shapeSize: 24,
    columnGap: 24,
    /** Room for the longest level word ("WARNING", "NO DATA") so numbers line up. */
    wordWidth: 140,
    barWidth: 90,
    barHeight: 12,
    limitWidth: 4,
    /** How far the warning-limit mark sticks out above and below its bar. */
    limitOverhang: 4,
  },
  /** The warning tone (scene/Tone.tsx): short and low, not a siren. */
  tone: {
    frequencyHz: 660,
    durationS: 0.25,
    gain: 0.2,
  },
  /** The rig that carries the panels: it follows the head with a delay and only turns. */
  rig: {
    distanceM,
    followS: 0.35, // time for the rig to close about 63% of the gap to the head's direction
  },
  /**
   * Where panels may go, in degrees from the rig's forward direction (yaw positive = to the
   * wearer's left, pitch positive = up). The centre stays clear (acceptance 8). Every panel must
   * fit inside `view`: the laptop camera sees ±30° up and down, an emulated Quest 3 eye about
   * ±41° sideways, less the eye's offset from the head's centre.
   */
  view: {
    clearYawDeg: 15,
    clearPitchDeg: 10,
    maxYawDeg: 39,
    maxPitchDeg: 28,
  },
  /** Laptop view: a fixed camera at standing eye height. */
  camera: {
    fovDeg: 60,
    eyeHeightM: 1.6,
    near: 0.05,
    far: 50,
  },
} as const;

export const LEVELS: readonly Level[] = ["nominal", "caution", "warning", "unknown", "stale", "off"];
