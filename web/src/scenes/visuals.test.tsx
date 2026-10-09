import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { AlertVisual } from "./visuals/AlertVisual";
import { ContactVisual, telHref } from "./visuals/ContactVisual";
import { StatVisual } from "./visuals/StatVisual";
import { TitleVisual } from "./visuals/TitleVisual";

afterEach(cleanup);

describe("TitleVisual", () => {
  test("shows the greeting and subheading without adding a heading", () => {
    const { container } = render(<TitleVisual visual={{ type: "title", heading: "Hello Priya", subheading: "Your offer" }} />);
    expect(container.textContent).toContain("Hello Priya");
    expect(container.textContent).toContain("Your offer");
    expect(screen.queryByRole("heading")).toBeNull();
  });
});

describe("StatVisual", () => {
  const visual = {
    type: "stat" as const,
    stats: [
      { label: "You're borrowing", value: "£256,500" },
      { label: "Your home is worth", value: "£285,000" },
    ],
    meter: { label: "Loan to value", value: 90, max: 100, unit: "%" },
  };

  test("pairs each label with its value in a description list", () => {
    const { container } = render(<StatVisual visual={visual} />);
    const terms = [...container.querySelectorAll("dt")].map((dt) => dt.textContent);
    const values = [...container.querySelectorAll("dd")].map((dd) => dd.textContent);
    expect(terms).toEqual(["You're borrowing", "Your home is worth"]);
    expect(values).toEqual(["£256,500", "£285,000"]);
  });

  test("writes the meter value as text, and hides the decorative bar", () => {
    const { container } = render(<StatVisual visual={visual} />);
    expect(screen.getByText("90%")).toBeTruthy();
    const track = container.querySelector(".stat-meter__track")!;
    expect(track.getAttribute("aria-hidden")).toBe("true");
    expect((track.firstElementChild as HTMLElement).style.width).toBe("90%");
  });

  test("no meter, no bar", () => {
    const { container } = render(<StatVisual visual={{ type: "stat", stats: visual.stats }} />);
    expect(container.querySelector(".stat-meter")).toBeNull();
  });
});

describe("AlertVisual", () => {
  test.each([
    ["info", "Note"],
    ["important", "Important"],
    ["danger", "Warning"],
  ] as const)("%s tone is labelled %j in words", (tone, label) => {
    render(<AlertVisual visual={{ type: "alert", tone, heading: "Heading", body: "Body" }} />);
    expect(screen.getByText(label)).toBeTruthy();
  });

  test("shows a body, or a list of items", () => {
    render(<AlertVisual visual={{ type: "alert", tone: "danger", heading: "Call us if you have:", items: ["Pain", "Fever"] }} />);
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual(["Pain", "Fever"]);
  });

  test("is not an interrupting live alert", () => {
    render(<AlertVisual visual={{ type: "alert", tone: "danger", heading: "Heading", body: "Body" }} />);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("ContactVisual", () => {
  test("phone numbers are tappable links with digits only", () => {
    expect(telHref("01632 960215")).toBe("tel:01632960215");
    render(<ContactVisual visual={{ type: "contact", phone: "01632 960215", secondary_phone: "01632 960999" }} />);
    expect(screen.getByRole("link", { name: "01632 960215" }).getAttribute("href")).toBe("tel:01632960215");
    expect(screen.getByRole("link", { name: "01632 960999" }).getAttribute("href")).toBe("tel:01632960999");
  });

  test("shows the reference and hours, and leaves out what's missing", () => {
    const { container } = render(
      <ContactVisual visual={{ type: "contact", phone: "01632 960412", reference: "FBS-2026-104381", hours: "Mon to Fri" }} />,
    );
    expect(container.textContent).toContain("FBS-2026-104381");
    expect(container.textContent).toContain("Mon to Fri");
    expect(container.textContent).not.toContain("Out of hours");
  });
});
