import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { packs } from "../data";
import type { Theme } from "../types";
import { googleFontsUrl, themeToCssVars } from "./theme";
import { ThemeProvider, useTheme } from "./ThemeProvider";

const theme: Theme = packs[0].theme;

function withFonts(heading: string, body: string): Theme {
  return { ...theme, font: { heading, body } };
}

describe("themeToCssVars", () => {
  test("every colour becomes a --color-* variable in kebab case", () => {
    const vars = themeToCssVars(theme);
    for (const [name, hex] of Object.entries(theme.color)) {
      const kebab = name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
      expect(vars[`--color-${kebab}`]).toBe(hex);
    }
    expect(vars["--color-surface-alt"]).toBe(theme.color.surfaceAlt);
  });

  test("fonts, radius and transition time become variables too", () => {
    const vars = themeToCssVars(withFonts("Fraunces", "Source Sans 3"));
    expect(vars["--font-heading"]).toBe('"Fraunces", system-ui, sans-serif');
    expect(vars["--font-body"]).toBe('"Source Sans 3", system-ui, sans-serif');
    expect(vars["--radius"]).toBe(theme.shape.radius);
    expect(vars["--transition-ms"]).toBe(`${theme.motion.scene_transition_ms}ms`);
  });
});

describe("googleFontsUrl", () => {
  test("lists two different fonts, with spaces as +", () => {
    expect(googleFontsUrl(withFonts("Fraunces", "Source Sans 3"))).toBe(
      "https://fonts.googleapis.com/css2?family=Fraunces:wght@400;700&family=Source+Sans+3:wght@400;700&display=swap",
    );
  });

  test("lists a font used for both headings and body only once", () => {
    const url = googleFontsUrl(withFonts("Atkinson Hyperlegible", "Atkinson Hyperlegible"));
    expect(url.match(/family=/g)).toHaveLength(1);
  });
});

describe("ThemeProvider", () => {
  afterEach(() => {
    cleanup();
    document.getElementById("theme-fonts")?.remove();
  });

  function BrandName() {
    return <p>{useTheme().brand.name}</p>;
  }

  test("puts the variables on its wrapper and shares the theme", () => {
    render(
      <ThemeProvider theme={theme}>
        <BrandName />
      </ThemeProvider>,
    );

    const wrapper = screen.getByText(theme.brand.name).parentElement!;
    expect(wrapper.style.getPropertyValue("--color-primary")).toBe(theme.color.primary);
  });

  test("adds one font stylesheet and updates it when the theme changes", () => {
    const other = withFonts("Fraunces", "Source Sans 3");
    const { rerender } = render(<ThemeProvider theme={theme}>x</ThemeProvider>);
    rerender(<ThemeProvider theme={other}>x</ThemeProvider>);

    const links = document.head.querySelectorAll("link#theme-fonts");
    expect(links).toHaveLength(1);
    expect((links[0] as HTMLLinkElement).href).toBe(googleFontsUrl(other));
  });

  test("useTheme outside a provider explains the mistake", () => {
    expect(() => render(<BrandName />)).toThrow("must be used inside <ThemeProvider>");
  });
});
