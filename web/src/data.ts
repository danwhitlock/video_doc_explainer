import type { Customer, Pack, ScenesFile, Theme } from "./types";

// Pack config is bundled at build time: every packs/<name>/ folder with a
// theme.json is picked up automatically, so the web app names no industry.
const themes = import.meta.glob<Theme>("../../packs/*/theme.json", { eager: true, import: "default" });
const customerLists = import.meta.glob<(Customer & { document?: string })[]>(
  "../../packs/*/customers.json",
  { eager: true, import: "default" },
);

function packName(path: string): string {
  // "../../packs/mortgage/theme.json" -> "mortgage"
  return path.split("/").at(-2)!;
}

export const packs: Pack[] = Object.entries(themes).map(([path, theme]) => {
  const name = packName(path);
  const listed = customerLists[`../../packs/${name}/customers.json`] ?? [];
  return {
    name,
    theme,
    // Copy only the fields the UI needs; the document path stays behind.
    customers: listed.map(({ id, preferred_name, persona, prefs }) => ({
      id,
      preferred_name,
      persona,
      prefs,
    })),
  };
});

/** Fetch one customer's pipeline output from web/public/data/. */
export async function loadScenes(pack: string, customer: string): Promise<ScenesFile> {
  const url = `/data/${pack}/${customer}/scenes.json`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`No explainer for ${pack}/${customer} (${response.status} from ${url})`);
  }
  const data = await response.json();
  // A light check only: the pipeline has already validated this file.
  // An empty list counts as missing: the player needs at least one scene.
  if (!Array.isArray(data?.scenes) || data.scenes.length === 0) {
    throw new Error(`${url} has no scenes`);
  }
  return data as ScenesFile;
}
