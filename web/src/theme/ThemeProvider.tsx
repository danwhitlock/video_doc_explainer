import { createContext, useContext, useEffect, type CSSProperties, type ReactNode } from "react";
import type { Theme } from "../types";
import { googleFontsUrl, themeToCssVars } from "./theme";

const FONT_LINK_ID = "theme-fonts";

const ThemeContext = createContext<Theme | null>(null);

/** The current pack's theme, for components that need more than CSS (e.g. voice settings). */
export function useTheme(): Theme {
  const theme = useContext(ThemeContext);
  if (theme === null) {
    throw new Error("useTheme() must be used inside <ThemeProvider>");
  }
  return theme;
}

export function ThemeProvider({ theme, children }: { theme: Theme; children: ReactNode }) {
  const fontsUrl = googleFontsUrl(theme);

  // The <head> is outside React's tree, so the font stylesheet is added there
  // as a side effect: one <link>, whose address changes with the theme.
  useEffect(() => {
    let link = document.getElementById(FONT_LINK_ID) as HTMLLinkElement | null;
    if (link === null) {
      link = document.createElement("link");
      link.id = FONT_LINK_ID;
      link.rel = "stylesheet";
      document.head.appendChild(link);
    }
    link.href = fontsUrl;
  }, [fontsUrl]);

  return (
    <ThemeContext.Provider value={theme}>
      {/* CSS custom properties set here are inherited by everything inside. */}
      <div className="theme-root" style={themeToCssVars(theme) as CSSProperties}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
}
