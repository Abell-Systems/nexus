import type { TopicMapResult } from "../domain/topicMap";
import provenance from "./data/provenance.json";
import { IntegrityError, loadVerifiedJson, type HashManifest } from "./verifiedLoader";

export const TOPICS: readonly { key: string; name: string }[] = [
  { key: "baterias", name: "Baterías" },
  { key: "solar", name: "Energía solar" },
];

// Hashes travel inside the bundle (build-time import), like the unobserved-pairs loader.
const defaultManifest: HashManifest = Object.fromEntries(
  provenance.files.filter((f) => f.served === "on_demand").map((f) => [`/data/${f.file}`, f.sha256]),
);

const cache = new Map<string, Promise<TopicMapResult>>();

export function loadTopicMap(
  topic: string,
  fetcher?: typeof fetch,
  manifest: HashManifest = defaultManifest,
): Promise<TopicMapResult> {
  let pending = cache.get(topic);
  if (!pending) {
    pending = loadVerifiedJson<TopicMapResult>(`/data/topic-map-${topic}.json`, manifest, fetcher).then((result) => {
      if (result.topic.key !== topic) throw new IntegrityError("topic key differs from the requested topic");
      return result;
    });
    cache.set(topic, pending);
    pending.catch(() => cache.delete(topic));
  }
  return pending;
}

export function resetTopicMapCache(): void {
  cache.clear();
}
