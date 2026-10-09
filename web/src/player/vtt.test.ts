import { describe, expect, test } from "vitest";
import type { ScenesFile } from "../types";
import { splitSentences } from "./sentences";
import { parseVtt } from "./vtt";

describe("parseVtt", () => {
  test("reads id, start, end and text of each cue", () => {
    const vtt = "WEBVTT\n\nwelcome-1\n00:00:00.000 --> 00:00:00.769\nHi Priya.\n\nwelcome-2\n00:00:00.769 --> 00:01:04.231\nThis explains your offer.\n";
    expect(parseVtt(vtt)).toEqual([
      { id: "welcome-1", start: 0, end: 0.769, text: "Hi Priya." },
      { id: "welcome-2", start: 0.769, end: 64.231, text: "This explains your offer." },
    ]);
  });

  test("accepts short times, Windows line endings and multi-line text", () => {
    const [cue] = parseVtt("WEBVTT\r\n\r\n00:04.500 --> 00:06.000\r\nTwo\r\nlines\r\n");
    expect(cue).toEqual({ id: "", start: 4.5, end: 6, text: "Two lines" });
  });

  test("rejects a file that isn't WebVTT", () => {
    expect(() => parseVtt("1\n00:00:00,000 --> 00:00:01,000\nSRT, not VTT")).toThrow("Not a WebVTT file");
  });
});

// Cross-check: for every customer, the pipeline's captions.vtt must contain
// exactly the sentences the player shows as captions, scene by scene, in order.
const captionFiles = import.meta.glob<string>("../../public/data/*/*/captions.vtt", {
  query: "?raw",
  import: "default",
  eager: true,
});
const scenesFiles = import.meta.glob<ScenesFile>("../../public/data/*/*/scenes.json", { eager: true, import: "default" });

const customers = Object.entries(scenesFiles).map(([path, file]) => {
  const vtt = captionFiles[path.replace("scenes.json", "captions.vtt")];
  return [`${file.pack}/${file.customer_id}`, file, vtt] as const;
});

describe("committed captions.vtt files", () => {
  test("every customer with scenes has captions", () => {
    expect(customers.length).toBeGreaterThan(0);
    for (const [, , vtt] of customers) expect(vtt).toBeTypeOf("string");
  });

  test.each(customers)("%s: cues are exactly the player's caption sentences", (_name, file, vtt) => {
    const expected = file.scenes.flatMap((scene) =>
      splitSentences(scene.narration).map((text, index) => ({ id: `${scene.id}-${index + 1}`, text })),
    );
    const actual = parseVtt(vtt).map(({ id, text }) => ({ id, text }));
    expect(actual).toEqual(expected);
  });
});
