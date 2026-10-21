import type { PairsResults } from "../domain/whitespace";

export const PAIRS_URL = "/data/oepm-subclass-pairs-results.json";

let cached: Promise<PairsResults> | undefined;

// The result is 6 MB: it is a static file fetched on first use, never part of the bundle.
export function loadSubclassPairs(fetcher: typeof fetch = fetch): Promise<PairsResults> {
  cached ??= fetcher(PAIRS_URL).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<PairsResults>;
  });
  cached.catch(() => { cached = undefined; });
  return cached;
}

export function resetSubclassPairsCache(): void {
  cached = undefined;
}
