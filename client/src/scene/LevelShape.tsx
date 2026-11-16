// The shape drawn next to a value. Which shape means which level is decided in theme.ts;
// this file only knows how to draw each one.
import { Svg } from "@react-three/uikit";
import type { Shape } from "../theme";

const box = (inner: string) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">${inner}</svg>`;

const DRAWING: Record<Shape, string> = {
  circle: box('<circle cx="12" cy="12" r="10"/>'),
  diamond: box('<path d="M12 1 L23 12 L12 23 L1 12 Z"/>'),
  triangle: box('<path d="M12 2 L23 22 L1 22 Z"/>'),
  ring: box('<path fill-rule="evenodd" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 5a5 5 0 1 1 0 10 5 5 0 0 1 0-10Z"/>'),
  square: box('<rect x="3" y="3" width="18" height="18"/>'),
};

export function LevelShape({ shape, color, size }: { shape: Shape; color: string; size: number }) {
  return <Svg content={DRAWING[shape]} color={color} width={size} height={size} flexShrink={0} />;
}
