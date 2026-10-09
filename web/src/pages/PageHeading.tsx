import { useEffect, useRef } from "react";

interface PageHeadingProps {
  children: string;
  /** The browser tab title for this page. */
  documentTitle: string;
  /** True after a navigation inside the app; false on the very first page load. */
  focusOnMount: boolean;
}

/**
 * Every page's <h1>. In a single-page app there's no reload when you
 * navigate, so the browser announces nothing; moving focus here makes a
 * screen reader read the new heading, and puts keyboard users at the top
 * of the new content. Not on first load: a fresh page already starts at the
 * top, and taking focus there would skip past the skip link.
 */
export function PageHeading({ children, documentTitle, focusOnMount }: PageHeadingProps) {
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = documentTitle;
  }, [documentTitle]);

  useEffect(() => {
    if (focusOnMount) {
      heading.current?.focus();
    }
    // Empty list: run once, when the page first appears, not on every re-render.
  }, []);

  // tabIndex={-1}: focusable from code, but not an extra Tab stop.
  return (
    <h1 ref={heading} tabIndex={-1} className="page-heading">
      {children}
    </h1>
  );
}
