import { afterEach, describe, expect, test, vi } from "vitest";
import { loadScenes, packs } from "./data";
import { VISUAL_TYPES, type ScenesFile } from "./types";

describe("packs", () => {
  test("finds every pack folder, each with its customers", () => {
    const names = packs.map((pack) => pack.name).sort();
    expect(names).toEqual(["healthcare", "mortgage"]);
    for (const pack of packs) {
      expect(pack.customers).toHaveLength(3);
      expect(pack.theme.brand.fictional).toBe(true);
    }
  });

  test("customer cards never carry the document path", () => {
    for (const customer of packs.flatMap((pack) => pack.customers)) {
      expect(Object.keys(customer).sort()).toEqual(["id", "persona", "preferred_name", "prefs"]);
    }
  });
});

describe("loadScenes", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("fetches the customer's scenes.json", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ scenes: [{ id: "welcome" }] })));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadScenes("mortgage", "m-001");

    expect(fetchMock).toHaveBeenCalledWith("/data/mortgage/m-001/scenes.json");
    expect(result.scenes).toEqual([{ id: "welcome" }]);
  });

  test("a file with no scenes counts as missing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ scenes: [] }))));

    await expect(loadScenes("mortgage", "m-001")).rejects.toThrow("has no scenes");
  });

  test("a missing file gives a clear error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 404 })));

    await expect(loadScenes("mortgage", "m-999")).rejects.toThrow("No explainer for mortgage/m-999 (404");
  });
});

// The real pipeline outputs, read at test time. JSON imports are typed loosely
// (a "type" is just string), so this checks the shapes at runtime instead.
const realOutputs = import.meta.glob<ScenesFile>("../public/data/*/*/scenes.json", {
  eager: true,
  import: "default",
});

describe("committed scenes.json files", () => {
  test("there is one for every customer", () => {
    const customerCount = packs.reduce((total, pack) => total + pack.customers.length, 0);
    expect(Object.keys(realOutputs)).toHaveLength(customerCount);
  });

  test.each(Object.entries(realOutputs))("%s matches the Scene shape", (_path, file) => {
    for (const scene of file.scenes) {
      expect(typeof scene.id).toBe("string");
      expect(typeof scene.title).toBe("string");
      expect(typeof scene.narration).toBe("string");
      expect(typeof scene.speech).toBe("string");
      expect(typeof scene.duration_seconds).toBe("number");
      expect(VISUAL_TYPES).toContain(scene.visual.type);
    }
  });
});
