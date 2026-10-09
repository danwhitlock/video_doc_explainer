import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { packs } from "../data";
import { ThemeProvider } from "../theme/ThemeProvider";
import type { Theme } from "../types";
import { BrandMark } from "./BrandMark";
import { Layout } from "./Layout";

afterEach(cleanup);

function renderLayout(theme: Theme) {
  return render(
    <ThemeProvider theme={theme}>
      <Layout homeHref="#/somewhere">
        <h1>Page heading</h1>
      </Layout>
    </ThemeProvider>,
  );
}

describe("Layout", () => {
  test.each(packs.map((pack) => [pack.name, pack.theme] as const))(
    "%s: has banner, main and footer landmarks, one h1",
    (_name, theme) => {
      renderLayout(theme);

      expect(screen.getByRole("banner")).toBeTruthy();
      expect(screen.getByRole("main")).toBeTruthy();
      expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    },
  );

  test("every screen shows the fictional-demonstrator disclaimer", () => {
    renderLayout(packs[0].theme);

    // "contentinfo" is the accessibility role of a page-level <footer>.
    const footer = screen.getByRole("contentinfo");
    expect(footer.textContent).toBe("Fictional demonstrator — not financial or medical advice");
  });

  test("the skip link is first and points at main", () => {
    const { container } = renderLayout(packs[0].theme);

    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(container.querySelector("a")).toBe(skip);
    expect(skip.getAttribute("href")).toBe(`#${screen.getByRole("main").id}`);
  });

  test("the header is read as the full brand name, not the wordmark", () => {
    // A made-up brand whose wordmark differs from its name, as Fernmoor's does.
    const base = packs[0].theme;
    renderLayout({ ...base, brand: { ...base.brand, name: "Quillbank Society", wordmark: "QUILL" } });

    expect(screen.getByText("QUILL").getAttribute("aria-hidden")).toBe("true");
    expect(screen.getByText("Quillbank Society home").className).toBe("visually-hidden");
  });

  test("the brand is a link home, named after the brand", () => {
    const theme = packs[0].theme;
    renderLayout(theme);

    const home = screen.getByRole("link", { name: `${theme.brand.name} home` });
    expect(home.getAttribute("href")).toBe("#/somewhere");
  });
});

describe("BrandMark", () => {
  test("is hidden from assistive technology", () => {
    const { container } = render(<BrandMark mark="leaf" name="Fernmoor" />);
    expect(container.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
  });

  test("an unknown mark falls back to the brand's first letter", () => {
    const { container } = render(<BrandMark mark="no-such-mark" name="Quillbank" />);
    expect(container.querySelector("text")?.textContent).toBe("Q");
  });

  test.each(packs.map((pack) => pack.theme.brand.mark))("%s is a known mark, not the fallback", (mark) => {
    const { container } = render(<BrandMark mark={mark} name="X" />);
    expect(container.querySelector("text")).toBeNull();
  });
});
