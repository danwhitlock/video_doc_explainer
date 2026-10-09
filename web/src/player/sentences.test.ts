import { describe, expect, test } from "vitest";
import type { ScenesFile } from "../types";
import { estimateSeconds, splitSentences } from "./sentences";

describe("splitSentences", () => {
  test("splits after . ! and ?, keeping the punctuation", () => {
    expect(splitSentences("Hi Priya. Ready? Let's go!")).toEqual(["Hi Priya.", "Ready?", "Let's go!"]);
  });

  test("doesn't split inside numbers like £1,359.76", () => {
    expect(splitSentences("You'll pay £1,359.76 a month. That's fixed.")).toEqual([
      "You'll pay £1,359.76 a month.",
      "That's fixed.",
    ]);
  });

  test("ignores surrounding and repeated whitespace", () => {
    expect(splitSentences("  One.\n\n Two.  ")).toEqual(["One.", "Two."]);
    expect(splitSentences("")).toEqual([]);
  });
});

describe("estimateSeconds", () => {
  test("is words divided by words per second", () => {
    expect(estimateSeconds("You'll pay £1,359.76 a month.", 2.6)).toBeCloseTo(5 / 2.6, 10);
  });
});

// Cross-check: narration (captions) and speech (spoken) must split into the
// same number of sentences, so sentence n spoken is always caption n shown.
const outputs = import.meta.glob<ScenesFile>("../../public/data/*/*/scenes.json", { eager: true, import: "default" });
const realScenes = Object.values(outputs).flatMap((file) =>
  file.scenes.map((scene) => [`${file.customer_id}/${scene.id}`, scene] as const),
);

describe("committed scenes", () => {
  test("there are real scenes to check", () => {
    expect(realScenes.length).toBeGreaterThan(0);
  });

  test.each(realScenes)("%s: narration and speech have the same sentences count", (_name, scene) => {
    expect(splitSentences(scene.speech)).toHaveLength(splitSentences(scene.narration).length);
  });
});
