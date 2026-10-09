// A small reader for WebVTT caption files, enough for the files our pipeline
// writes (pipeline/render.py): a "WEBVTT" header, then blocks of
//   id
//   00:00:04.231 --> 00:00:06.154
//   text (one or more lines)

export interface Cue {
  id: string;
  start: number; // seconds
  end: number;
  text: string;
}

/** "00:00:04.231" or "00:04.231" -> 4.231 seconds. */
function toSeconds(time: string): number {
  return time
    .trim()
    .split(":")
    .reduce((total, part) => total * 60 + Number(part), 0);
}

export function parseVtt(source: string): Cue[] {
  const [header, ...blocks] = source.replace(/\r\n/g, "\n").trim().split(/\n{2,}/);
  if (!header.startsWith("WEBVTT")) {
    throw new Error("Not a WebVTT file: it must start with WEBVTT");
  }
  return blocks.map((block) => {
    const lines = block.split("\n");
    const timing = lines.findIndex((line) => line.includes("-->"));
    if (timing === -1) {
      throw new Error(`Cue without a timing line: ${JSON.stringify(block)}`);
    }
    const [start, end] = lines[timing].split("-->");
    return {
      id: timing > 0 ? lines[0] : "",
      start: toSeconds(start),
      end: toSeconds(end),
      text: lines.slice(timing + 1).join(" "),
    };
  });
}
