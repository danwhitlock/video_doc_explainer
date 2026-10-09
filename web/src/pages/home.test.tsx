import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { packs } from "../data";
import { Home } from "./Home";

afterEach(cleanup);

const current = packs[1];

function renderHome() {
  return render(<Home pack={current} packs={packs} />);
}

describe("Home", () => {
  test("has exactly one h1", () => {
    renderHome();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  test("the switcher links to every pack's home", () => {
    renderHome();
    const nav = screen.getByRole("navigation", { name: "Choose an industry" });

    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual(packs.map((pack) => `#/${pack.name}`));
  });

  test("only the current pack is marked current, in text as well as aria-current", () => {
    renderHome();
    const nav = screen.getByRole("navigation", { name: "Choose an industry" });

    const marked = within(nav)
      .getAllByRole("link")
      .filter((link) => link.getAttribute("aria-current") === "page");
    expect(marked).toHaveLength(1);
    expect(marked[0].textContent).toContain(current.theme.brand.name);
    expect(marked[0].textContent).toContain("Showing");
  });

  test("shows a card per customer, linking to their explainer", () => {
    renderHome();
    const section = screen.getByRole("region", { name: "Choose a customer" });

    const cards = within(section).getAllByRole("listitem");
    expect(cards).toHaveLength(current.customers.length);
    current.customers.forEach((customer, index) => {
      const link = within(cards[index]).getByRole("link", { name: customer.preferred_name });
      expect(link.getAttribute("href")).toBe(`#/${current.name}/${customer.id}`);
      expect(cards[index].textContent).toContain(customer.persona);
    });
  });
});
