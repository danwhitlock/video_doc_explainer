// npm run check:themes - fails (exit code 1) if any pack's theme.json has a
// contrast pair below its minimum, or a pair naming a colour it doesn't define.
// Runs on every packs/*/theme.json, so a new pack is checked with no changes here.

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { contrastRatio } from "../src/contrast.ts";
import type { Theme } from "../src/types.ts";

const packsDir = join(import.meta.dirname, "..", "..", "packs");
let failures = 0;

for (const pack of readdirSync(packsDir).sort()) {
  let theme: Theme;
  try {
    theme = JSON.parse(readFileSync(join(packsDir, pack, "theme.json"), "utf8"));
  } catch {
    continue; // not a pack folder (no theme.json)
  }
  console.log(`\n${pack}`);
  for (const { fg, bg, min } of theme.contrast_pairs) {
    const fgHex = theme.color[fg];
    const bgHex = theme.color[bg];
    if (fgHex === undefined || bgHex === undefined) {
      console.log(`  FAIL  ${fg} on ${bg}: colour not defined in theme.color`);
      failures++;
      continue;
    }
    const ratio = contrastRatio(fgHex, bgHex);
    const passed = ratio >= min;
    if (!passed) failures++;
    // Show 2 decimals, but compare the unrounded ratio, so 4.496 can't pass as "4.50".
    console.log(`  ${passed ? "pass" : "FAIL"}  ${fg} on ${bg}: ${ratio.toFixed(2)}:1 (min ${min}:1)`);
  }
}

console.log(failures === 0 ? "\nAll contrast pairs pass." : `\n${failures} contrast pair(s) fail.`);
process.exitCode = failures === 0 ? 0 : 1;
