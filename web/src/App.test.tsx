import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import App from "./App";

afterEach(cleanup);

test("every screen shows the fictional-demonstrator disclaimer", () => {
  render(<App />);

  // "contentinfo" is the accessibility role of a page-level <footer>;
  // getByRole throws if there isn't exactly one, so finding it is part of the check.
  const footer = screen.getByRole("contentinfo");
  expect(footer.textContent).toBe("Fictional demonstrator — not financial or medical advice");
});
