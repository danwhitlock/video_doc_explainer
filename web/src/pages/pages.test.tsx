import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { packs } from "../data";
import { CustomerPage } from "./CustomerPage";
import { PageHeading } from "./PageHeading";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("PageHeading", () => {
  test("sets the browser tab title", () => {
    render(<PageHeading documentTitle="Priya's explainer — Fernmoor" focusOnMount={false}>Heading</PageHeading>);
    expect(document.title).toBe("Priya's explainer — Fernmoor");
  });

  test("takes focus when it appears after a navigation", () => {
    render(<PageHeading documentTitle="t" focusOnMount={true}>Heading</PageHeading>);
    expect(document.activeElement).toBe(screen.getByRole("heading", { level: 1 }));
  });

  test("leaves focus alone on the first page load", () => {
    render(<PageHeading documentTitle="t" focusOnMount={false}>Heading</PageHeading>);
    expect(document.activeElement).toBe(document.body);
  });
});

describe("CustomerPage", () => {
  const pack = packs[0];
  const customer = pack.customers[0];

  test("names the customer and links back to the pack's home", async () => {
    // CustomerPage fetches scenes; answer with none, so the test needs no server.
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ scenes: [] }))));
    render(<CustomerPage pack={pack} customer={customer} navigated={false} />);

    expect(screen.getByRole("heading", { level: 1 }).textContent).toContain(customer.preferred_name);
    expect(screen.getByRole("link", { name: "← All customers" }).getAttribute("href")).toBe(`#/${pack.name}`);
    await screen.findByRole("list"); // let the fetch finish before the test ends
  });
});
