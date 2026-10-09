import { useEffect, useState } from "react";
import type { Customer, Pack } from "./types";

// Hash URLs: "#/mortgage" (a pack's home) and "#/mortgage/m-001" (one explainer).
// The part after "#" never reaches the server, so this works on any static host
// with no rewrite rules.

export interface Route {
  pack: Pack;
  customer: Customer | null; // null = the pack's home page
}

/**
 * Read a hash like "#/mortgage/m-001". Only names that really exist in `packs`
 * are accepted, so a typed URL can never point the app at an unexpected file.
 * Anything unrecognised falls back to the first pack's home.
 */
export function parseRoute(hash: string, packs: Pack[]): Route {
  const [packName, customerId] = hash.replace(/^#\/?/, "").split("/");
  const pack = packs.find((candidate) => candidate.name === packName);
  if (pack === undefined) {
    return { pack: packs[0], customer: null };
  }
  const customer = pack.customers.find((candidate) => candidate.id === customerId) ?? null;
  return { pack, customer };
}

/** The hash for a pack's home, or for one customer's explainer. */
export function routeHref(packName: string, customerId?: string): string {
  return customerId === undefined ? `#/${packName}` : `#/${packName}/${customerId}`;
}

/** The current route, updated whenever the hash changes (links, Back, Forward, typing). */
export function useRoute(packs: Pack[]): Route {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return parseRoute(hash, packs);
}
