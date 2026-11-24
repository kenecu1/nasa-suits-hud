// Contrast of text on a translucent backing (WCAG relative luminance). Decision F in
// docs/briefs/M2.md: the backing is mixed with white at its opacity, the worst case for a dark
// panel, because a bright lamp may stand behind it.

type Rgb = readonly [number, number, number];

/** "#rrggbb" to 0..255 channels. Throws on anything else, so a typo in theme.ts fails a test. */
export function parseHex(hex: string): Rgb {
  const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (match === null) throw new Error(`not a #rrggbb colour: ${hex}`);
  return [parseInt(match[1] as string, 16), parseInt(match[2] as string, 16), parseInt(match[3] as string, 16)];
}

/** `top` at `opacity` over an opaque `under`, per channel in sRGB (as the GPU blends it). */
export function composite(top: string, opacity: number, under: string): Rgb {
  const a = parseHex(top);
  const b = parseHex(under);
  return [0, 1, 2].map((i) => (a[i] as number) * opacity + (b[i] as number) * (1 - opacity)) as unknown as Rgb;
}

function channel(c: number): number {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

export function luminance(rgb: Rgb): number {
  return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2]);
}

/** (lighter + 0.05) / (darker + 0.05), from 1 to 21. */
export function contrastRatio(a: Rgb, b: Rgb): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}
