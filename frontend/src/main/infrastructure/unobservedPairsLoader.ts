import type { UnobservedPairsResults } from "../domain/whitespace";
import provenance from "./data/provenance.json";
import { loadVerifiedJson, type HashManifest } from "./verifiedLoader";

export const UNOBSERVED_PAIRS_URL = "/data/oepm-unobserved-pairs-results.json";

// The hashes travel inside the script bundle (build-time import), never fetched separately (contract section 6.1).
export const manifest: HashManifest = Object.fromEntries(
  provenance.files.filter((f) => f.served === "on_demand").map((f) => [`/data/${f.file}`, f.sha256]),
);

let cached: Promise<UnobservedPairsResults> | undefined;

// The only way vertical 3 data reaches the screen: through the verified loader.
export function loadUnobservedPairs(fetcher?: typeof fetch): Promise<UnobservedPairsResults> {
  cached ??= loadVerifiedJson<UnobservedPairsResults>(UNOBSERVED_PAIRS_URL, manifest, fetcher);
  cached.catch(() => { cached = undefined; });
  return cached;
}

export function resetUnobservedPairsCache(): void {
  cached = undefined;
}
