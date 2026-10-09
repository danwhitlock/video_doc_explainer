import type { Theme } from "../types";

/** "surfaceAlt" -> "surface-alt", the usual CSS naming style. */
function kebab(name: string): string {
  return name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
}

/** A font family as CSS: the theme's font first, then a safe fallback while it loads. */
function fontStack(family: string): string {
  return `"${family}", system-ui, sans-serif`;
}

/**
 * Every design token in the theme as a CSS custom property, e.g.
 * color.surfaceAlt -> "--color-surface-alt": "#EFE8DA".
 * Stylesheets use only these, so a new theme needs no CSS changes.
 */
export function themeToCssVars(theme: Theme): Record<string, string> {
  const vars: Record<string, string> = {};
  for (const [name, hex] of Object.entries(theme.color)) {
    vars[`--color-${kebab(name)}`] = hex;
  }
  vars["--font-heading"] = fontStack(theme.font.heading);
  vars["--font-body"] = fontStack(theme.font.body);
  vars["--radius"] = theme.shape.radius;
  vars["--transition-ms"] = `${theme.motion.scene_transition_ms}ms`;
  return vars;
}

/** One Google Fonts stylesheet URL for the theme's fonts, each family listed once. */
export function googleFontsUrl(theme: Theme): string {
  const families = [...new Set([theme.font.heading, theme.font.body])];
  // Spaces become "+"; 400 and 700 cover body text and headings.
  const params = families.map((family) => `family=${family.replaceAll(" ", "+")}:wght@400;700`);
  return `https://fonts.googleapis.com/css2?${params.join("&")}&display=swap`;
}
