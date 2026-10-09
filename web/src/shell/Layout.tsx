import type { ReactNode } from "react";
import { useTheme } from "../theme/ThemeProvider";
import { BrandMark } from "./BrandMark";

/** The frame around every screen: skip link, branded header, main area, disclaimer footer. */
export function Layout({ children }: { children: ReactNode }) {
  const { brand } = useTheme();

  return (
    <>
      {/* WCAG 2.4.1 Bypass Blocks: first thing a keyboard user reaches; hidden until focused. */}
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="site-header">
        <div className="site-header__inner">
          <BrandMark mark={brand.mark} name={brand.name} />
          <p className="site-header__brand">
            {/* Shown as the wordmark (e.g. "FERNMOOR"), but read aloud as the full name:
                some screen readers spell all-capitals words letter by letter. */}
            <span aria-hidden="true">{brand.wordmark}</span>
            <span className="visually-hidden">{brand.name}</span>
          </p>
          <p className="site-header__tagline">{brand.tagline}</p>
        </div>
      </header>
      {/* tabIndex={-1} lets the skip link move focus here, without adding a Tab stop. */}
      <main id="main" className="site-main" tabIndex={-1}>
        {children}
      </main>
      <footer className="site-footer">
        <p>Fictional demonstrator — not financial or medical advice</p>
      </footer>
    </>
  );
}
