import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { AlertVisual } from "./visuals/AlertVisual";
import { ChecklistVisual } from "./visuals/ChecklistVisual";
import { ComparisonVisual } from "./visuals/ComparisonVisual";
import { ContactVisual, telHref } from "./visuals/ContactVisual";
import { StatVisual } from "./visuals/StatVisual";
import { TableVisual } from "./visuals/TableVisual";
import { TimelineVisual } from "./visuals/TimelineVisual";
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

describe("ComparisonVisual", () => {
  const visual = {
    type: "comparison" as const,
    before: { label: "Until 31 October 2028", value: "£1,359.76", caption: "4.89% fixed" },
    after: { label: "After that", value: "£1,770.43", caption: "7.49% variable" },
    delta: "£410.67 more a month",
  };

  test("shows before, then after, then the difference in words", () => {
    const { container } = render(<ComparisonVisual visual={visual} />);
    const text = container.textContent!;
    expect(text.indexOf("£1,359.76")).toBeLessThan(text.indexOf("£1,770.43"));
    expect(text).toContain("4.89% fixed");
    expect(text).toContain("£410.67 more a month");
  });

  test("the arrow is decorative", () => {
    render(<ComparisonVisual visual={visual} />);
    expect(screen.getByText("→").getAttribute("aria-hidden")).toBe("true");
  });
});

describe("TimelineVisual", () => {
  const items = [
    { time: "9am the day before", label: "Last food" },
    { time: "11am on the day", label: "Last drink" },
    { time: "1pm on the day", label: "Arrive" },
  ];

  test("is an ordered list, in the data's order", () => {
    const { container } = render(<TimelineVisual visual={{ type: "timeline", items }} />);
    const list = container.querySelector("ol")!;
    const entries = within(list).getAllByRole("listitem");
    expect(entries.map((entry) => entry.textContent)).toEqual([
      "9am the day beforeLast food",
      "11am on the dayLast drink",
      "1pm on the dayArrive",
    ]);
  });

  test("says its tone in words, unless it's plain info", () => {
    render(<TimelineVisual visual={{ type: "timeline", tone: "important", items }} />);
    expect(screen.getByText("Important")).toBeTruthy();
    cleanup();
    render(<TimelineVisual visual={{ type: "timeline", tone: "info", items }} />);
    expect(screen.queryByText("Note")).toBeNull();
  });
});

describe("TableVisual", () => {
  const visual = {
    type: "table" as const,
    columns: ["Period", "Charge on the amount repaid"],
    rows: [
      ["Year 1", "2%"],
      ["Year 2", "1%"],
    ],
    footnote: "Overpay up to 10% a year with no charge.",
  };

  test("has column headers and a header for each row", () => {
    render(<TableVisual visual={visual} />);
    expect(screen.getAllByRole("columnheader").map((th) => th.textContent)).toEqual(visual.columns);
    expect(screen.getAllByRole("rowheader").map((th) => th.textContent)).toEqual(["Year 1", "Year 2"]);
    expect(screen.getAllByRole("cell").map((td) => td.textContent)).toEqual(["2%", "1%"]);
  });

  test("shows the footnote", () => {
    render(<TableVisual visual={visual} />);
    expect(screen.getByText(visual.footnote)).toBeTruthy();
  });
});

describe("ChecklistVisual", () => {
  test("lists the items, with no checkboxes", () => {
    render(<ChecklistVisual visual={{ type: "checklist", items: ["Bring your letter", "Arrange a lift home"] }} />);
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual(["Bring your letter", "Arrange a lift home"]);
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});
