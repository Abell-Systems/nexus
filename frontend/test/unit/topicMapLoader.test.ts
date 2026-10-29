import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { sha256Hex } from "../../src/main/infrastructure/sha256";
import { IntegrityError, LoadError } from "../../src/main/infrastructure/verifiedLoader";
import { loadTopicMap, resetTopicMapCache, TOPICS } from "../../src/main/infrastructure/topicMapLoader";
import type { TopicMapResult } from "../../src/main/domain/topicMap";

const URL_ = "/data/topic-map-synthetic.json";
const result: TopicMapResult = {
  schema: "topic-map/1",
  configuration: {
    id: "c",
    parameters: {
      schema: "topic-map/1", definition_id: "d", applicant_rules_id: "r",
      min_observed: 30, min_expected: 30, max_ratio: 0.8, unit: "O4",
    },
  },
  corpus: { source_id: "s", files: { "a.csv": "h" } },
  names_reviewed: true,
  unreviewed: [],
  topic: { key: "synthetic", name: "Sintético", noun: "cosas", joined: "con cosas" },
  total_documents: 3,
  corpus_documents: 10,
  years: [2011, 2012],
  trend: [
    { year: 2011, documents: 1, share: 10, ep_documents: 0 },
    { year: 2012, documents: 2, share: 20, ep_documents: 1 },
  ],
  ep_share: 0.5,
  top_applicant_recent: { name: "Acme", by_year: [1, 2] },
  subareas: [{ key: "k", name: "K", description: "d", documents: 2, series: [1, 1] }],
  neighbours: [{ subclass: "H01M", name: "Pilas", documents: 2 }],
  rare: [{ subclass: "H01M", name: "Pilas", observed: 30, expected: 31.5, ratio: 0.5 }],
  applicants: [{ name: "Acme", documents: 3, originals: ["ACME SL"] }],
};
const bytes = new TextEncoder().encode(JSON.stringify(result));
const manifest = { [URL_]: sha256Hex(bytes) };
const respond = (b: Uint8Array, status = 200) =>
  vi.fn(async () => new Response(b, { status })) as unknown as typeof fetch;

beforeEach(resetTopicMapCache);
afterEach(() => vi.restoreAllMocks());

describe("loadTopicMap", () => {
  it("shouldLoadAVerifiedTopic", async () => {
    const fetcher = respond(bytes);
    await expect(loadTopicMap("synthetic", fetcher, manifest)).resolves.toEqual(result);
    expect(fetcher).toHaveBeenCalledWith(URL_, { cache: "no-store" });
  });

  it("shouldRejectWhenTheHashDiffers", async () => {
    const changed = new TextEncoder().encode(JSON.stringify(result).replace("Acme", "Acmf"));
    await expect(loadTopicMap("synthetic", respond(changed), manifest)).rejects.toBeInstanceOf(IntegrityError);
  });

  it("shouldParseNothingWhenTheHashDiffers", async () => {
    const parse = vi.spyOn(JSON, "parse");
    await expect(loadTopicMap("synthetic", respond(bytes.slice(1)), manifest)).rejects.toBeInstanceOf(IntegrityError);
    expect(parse).not.toHaveBeenCalled();
  });

  it("shouldRejectWhenTheManifestHasNoEntryForTheTopic", async () => {
    await expect(loadTopicMap("synthetic", respond(bytes), {})).rejects.toBeInstanceOf(IntegrityError);
  });

  it("shouldRejectWhenTheKeyDiffersFromTheRequestedTopic", async () => {
    const other = "/data/topic-map-other.json";
    await expect(loadTopicMap("other", respond(bytes), { [other]: manifest[URL_] })).rejects.toBeInstanceOf(IntegrityError);
  });

  it("shouldFailWhenTheFileAnswers404", async () => {
    await expect(loadTopicMap("synthetic", respond(bytes, 404), manifest)).rejects.toBeInstanceOf(LoadError);
  });

  it("shouldNotCacheAFailure", async () => {
    await expect(loadTopicMap("synthetic", respond(bytes, 404), manifest)).rejects.toBeInstanceOf(LoadError);
    const fetcher = respond(bytes);
    await expect(loadTopicMap("synthetic", fetcher, manifest)).resolves.toEqual(result);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("shouldFetchOnceWhenTheSameTopicIsLoadedTwice", async () => {
    const fetcher = respond(bytes);
    await loadTopicMap("synthetic", fetcher, manifest);
    await loadTopicMap("synthetic", fetcher, manifest);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("shouldKeepTopicsApartWhenTheyAreCached", async () => {
    const other = "/data/topic-map-other.json";
    const otherBytes = new TextEncoder().encode(JSON.stringify({ ...result, topic: { ...result.topic, key: "other" } }));
    const both = { ...manifest, [other]: sha256Hex(otherBytes) };
    const fetcher = vi.fn(async (u: RequestInfo | URL) => new Response(u === other ? otherBytes : bytes)) as unknown as typeof fetch;
    await loadTopicMap("synthetic", fetcher, both);
    await loadTopicMap("other", fetcher, both);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("shouldNotLoadTheRealTopicsWhileTheDefaultManifestHasNoEntryForThem", async () => {
    for (const { key } of TOPICS) {
      await expect(loadTopicMap(key, respond(bytes))).rejects.toBeInstanceOf(IntegrityError);
    }
  });
});
