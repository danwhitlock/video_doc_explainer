// WCAG 2.2 contrast ratio, implemented from the spec's definitions:
// https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio

/** "#0E4D4A" -> [14, 77, 74]. Only 6-digit hex, so a typo can't slip through. */
export function hexToRgb(hex: string): [number, number, number] {
  const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (!match) {
    throw new Error(`Not a 6-digit hex colour: ${JSON.stringify(hex)}`);
  }
  return [parseInt(match[1], 16), parseInt(match[2], 16), parseInt(match[3], 16)];
}

/** Perceived brightness from 0 (black) to 1 (white). */
export function relativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((channel) => {
    const c = channel / 255;
    // Undo the sRGB gamma curve: screens store colours non-linearly.
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  // Green looks brightest to human eyes, blue darkest.
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** From 1 (same colour) to 21 (black on white). Order of arguments doesn't matter. */
export function contrastRatio(foreground: string, background: string): number {
  const a = relativeLuminance(foreground);
  const b = relativeLuminance(background);
  const [lighter, darker] = a > b ? [a, b] : [b, a];
  return (lighter + 0.05) / (darker + 0.05);
}
