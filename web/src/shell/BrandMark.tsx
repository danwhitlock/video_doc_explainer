import type { ReactNode } from "react";

// A small library of generic shapes, chosen by theme.brand.mark. Keyed by
// shape name, not by industry, so any pack can pick any mark.
// fill="currentColor" makes each mark take the text colour around it.
const MARKS: Record<string, ReactNode> = {
  leaf: (
    <>
      <path d="M5 19C5 10 11 4 20 4c0 9-6 15-15 15z" fill="currentColor" />
      <path d="M5 19l8-8" stroke="var(--color-primary)" strokeWidth="1.5" strokeLinecap="round" />
    </>
  ),
  "cross-circle": (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M10 6h4v4h4v4h-4v4h-4v-4H6v-4h4z" fill="currentColor" />
    </>
  ),
};

/** Decorative brand mark. Hidden from assistive technology: the brand name beside it says who this is. */
export function BrandMark({ mark, name }: { mark: string; name: string }) {
  const shape = MARKS[mark] ?? (
    // Unknown mark name: fall back to a monogram rather than showing nothing.
    <>
      <circle cx="12" cy="12" r="11" fill="currentColor" />
      <text x="12" y="16.5" textAnchor="middle" fontSize="13" fontWeight="700" fill="var(--color-primary)">
        {name.charAt(0)}
      </text>
    </>
  );
  return (
    <svg className="brand-mark" viewBox="0 0 24 24" width="32" height="32" aria-hidden="true" focusable="false">
      {shape}
    </svg>
  );
}
