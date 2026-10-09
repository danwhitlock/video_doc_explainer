import { useEffect, useState } from "react";
import { loadScenes } from "../data";
import type { ScenesFile } from "../types";

/** One of three states, so the page has to handle each (like Visual's union). */
export type ScenesState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; file: ScenesFile };

/** Fetch one customer's scenes.json, re-fetching when the pack or customer changes. */
export function useScenes(pack: string, customer: string): ScenesState {
  const [state, setState] = useState<ScenesState>({ status: "loading" });

  useEffect(() => {
    // If the customer changes before this request finishes, ignore its reply,
    // so a slow answer for Priya can't overwrite Gareth's page.
    let stale = false;
    setState({ status: "loading" });
    loadScenes(pack, customer).then(
      (file) => {
        if (!stale) setState({ status: "ready", file });
      },
      (error: unknown) => {
        if (!stale) setState({ status: "error", message: error instanceof Error ? error.message : String(error) });
      },
    );
    return () => {
      stale = true;
    };
  }, [pack, customer]);

  return state;
}
