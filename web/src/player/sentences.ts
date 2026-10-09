// The same sentence rule as the pipeline's split_sentences() in
// pipeline/readability.py: a sentence ends at . ! or ? followed by whitespace,
// so the "." in "£1,359.76" doesn't end one. Kept in step with the Python by a
// test that checks every committed scene (sentences.test.ts).
// Python uses a lookbehind, (?<=[.!?])\s+; this marks each break with a
// character that can't appear in text, then splits on it, because Safari
// before 16.4 can't parse lookbehinds and the whole app would fail to load.
const BREAK_MARK = "\u0000";

export function splitSentences(text: string): string[] {
  return text
    .trim()
    .replace(/([.!?])\s+/g, `$1${BREAK_MARK}`)
    .split(BREAK_MARK)
    .filter((sentence) => sentence !== "");
}

/** Estimated seconds to say a sentence: words ÷ words per second (the pipeline's caption rule). */
export function estimateSeconds(sentence: string, wordsPerSecond: number): number {
  const words = sentence.split(/\s+/).filter((word) => word !== "").length;
  return words / wordsPerSecond;
}
