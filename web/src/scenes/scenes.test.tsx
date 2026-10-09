import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { packs } from "../data";
import { CustomerPage } from "../pages/CustomerPage";
import { VISUAL_TYPES, type Scene, type ScenesFile, type Visual } from "../types";
import { SceneVisual } from "./SceneVisual";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// One real example of each visual type, taken from the committed pipeline outputs.
const outputs = import.meta.glob<ScenesFile>("../../public/data/*/*/scenes.json", { eager: true, import: "default" });
const exampleOf = new Map<string, Visual>();
for (const file of Object.values(outputs)) {
  for (const scene of file.scenes) {
    if (!exampleOf.has(scene.visual.type)) exampleOf.set(scene.visual.type, scene.visual);
  }
}

const pack = packs[0];
const customer = pack.customers[0];

function scene(id: string, title: string): Scene {
  return {
    id,
    title,
    visual: { type: "title", heading: title },
    narration: `${title} narration.`,
    speech: `${title} narration.`,
    start_seconds: 0,
    duration_seconds: 1,
  };
}

function scenesFile(...scenes: Scene[]): ScenesFile {
  return { pack: pack.name, customer_id: customer.id, words_per_second: 2.6, total_seconds: 1, scenes };
}

function respondWith(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

describe("CustomerPage loading scenes", () => {
  test("shows loading, then every scene in order", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respondWith(scenesFile(scene("a", "First"), scene("b", "Second")))));
    render(<CustomerPage pack={pack} customer={customer} navigated={false} />);

    expect(screen.getByRole("status").textContent).toContain("Loading");
    const headings = await screen.findAllByRole("heading", { level: 2 });
    expect(headings.map((heading) => heading.textContent)).toEqual(["First", "Second"]);
    expect(screen.getByText("First narration.")).toBeTruthy();
  });

  test("a missing file shows an error, and the way back stays", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 404 })));
    render(<CustomerPage pack={pack} customer={customer} navigated={false} />);

    expect((await screen.findByRole("alert")).textContent).toContain("isn't available");
    expect(screen.getByRole("link", { name: "← All customers" })).toBeTruthy();
  });

  test("a slow reply for the previous customer can't overwrite the current one", async () => {
    let answerFirst!: (response: Response) => void;
    const slow = new Promise<Response>((resolve) => (answerFirst = resolve));
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(slow)
      .mockResolvedValueOnce(respondWith(scenesFile(scene("now", "Current customer"))));
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(<CustomerPage pack={pack} customer={customer} navigated={false} />);
    rerender(<CustomerPage pack={pack} customer={pack.customers[1]} navigated={false} />);
    await screen.findByText("Current customer");

    answerFirst(respondWith(scenesFile(scene("old", "Previous customer"))));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText("Previous customer")).toBeNull();
  });
});

describe("SceneVisual", () => {
  test("the outputs include an example of every visual type", () => {
    expect([...exampleOf.keys()].sort()).toEqual([...VISUAL_TYPES].sort());
  });

  test.each(VISUAL_TYPES)("renders a real %s visual", (type) => {
    const { container } = render(<SceneVisual visual={exampleOf.get(type)!} />);
    expect(container.textContent).not.toBe("");
  });
});
