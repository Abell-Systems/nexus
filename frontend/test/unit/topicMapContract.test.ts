import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import { TopicMapPage } from "../../src/main/components/TopicMap/TopicMapPage";
import { dominantApplicant, periodEpShare } from "../../src/main/application/topicSummary";
import type { TopicMapResult } from "../../src/main/domain/topicMap";

// The producer's synthetic sample (backend test_topic_map.py compares it byte for byte with build_topic_result).
const SAMPLE = join(dirname(fileURLToPath(import.meta.url)), "../../../contracts/topic-map/1/synthetic-result.json");
const result = JSON.parse(readFileSync(SAMPLE, "utf-8")) as TopicMapResult;

// Typed against the interface: the compiler fails when a list and the interface diverge (extra or missing key).
type Keys<T> = Record<keyof T, true>;
const KEYS = {
  root: { schema: true, configuration: true, corpus: true, names_reviewed: true, unreviewed: true, topic: true, total_documents: true, corpus_documents: true, years: true, trend: true, ep_share: true, top_applicant_recent: true, subareas: true, neighbours: true, rare: true, applicants: true } satisfies Keys<TopicMapResult>,
  configuration: { id: true, parameters: true } satisfies Keys<TopicMapResult["configuration"]>,
  parameters: { schema: true, definition_id: true, applicant_rules_id: true, min_observed: true, min_expected: true, max_ratio: true, unit: true } satisfies Keys<TopicMapResult["configuration"]["parameters"]>,
  corpus: { source_id: true, files: true } satisfies Keys<TopicMapResult["corpus"]>,
  topic: { key: true, name: true, noun: true, joined: true } satisfies Keys<TopicMapResult["topic"]>,
  trend: { year: true, documents: true, share: true, ep_documents: true } satisfies Keys<TopicMapResult["trend"][number]>,
  recent: { name: true, by_year: true } satisfies Keys<NonNullable<TopicMapResult["top_applicant_recent"]>>,
  subarea: { key: true, name: true, description: true, documents: true, series: true } satisfies Keys<TopicMapResult["subareas"][number]>,
  neighbour: { subclass: true, name: true, documents: true } satisfies Keys<TopicMapResult["neighbours"][number]>,
  rare: { subclass: true, name: true, observed: true, expected: true, ratio: true } satisfies Keys<TopicMapResult["rare"][number]>,
  applicant: { name: true, documents: true, originals: true } satisfies Keys<TopicMapResult["applicants"][number]>,
};

const keysOf = (o: object) => Object.keys(o).sort();
const same = (actual: object, expected: object) => expect(keysOf(actual)).toEqual(keysOf(expected));

describe("topic-map/1 contract", () => {
  it("shouldHaveExactlyTheFieldsOfTheTypeWhenReadingTheSample", () => {
    same(result, KEYS.root);
    same(result.configuration, KEYS.configuration);
    same(result.configuration.parameters, KEYS.parameters);
    same(result.corpus, KEYS.corpus);
    same(result.topic, KEYS.topic);
    same(result.top_applicant_recent!, KEYS.recent);
    for (const [rows, keys] of [
      [result.trend, KEYS.trend],
      [result.subareas, KEYS.subarea],
      [result.neighbours, KEYS.neighbour],
      [result.rare, KEYS.rare],
      [result.applicants, KEYS.applicant],
    ] as const) {
      expect(rows.length).toBeGreaterThan(0); // an empty list would prove nothing about its rows
      rows.forEach((row) => same(row, keys));
    }
  });

  it("shouldHaveTheTypesTheViewsAssumeWhenReadingTheSample", () => {
    expect(result.schema).toBe("topic-map/1");
    expect(result.years).toEqual([...result.years].sort((a, b) => a - b));
    expect(result.years).not.toContain(2010);
    expect(result.trend.map((t) => t.year)).toEqual(result.years);
    expect(result.top_applicant_recent!.by_year).toHaveLength(result.years.length);
    result.trend.forEach((t) => {
      expect(Number.isInteger(t.documents) && Number.isInteger(t.ep_documents)).toBe(true);
      expect(t.ep_documents).toBeLessThanOrEqual(t.documents);
    });
    result.rare.forEach((r) => {
      expect(r.observed).toBeGreaterThanOrEqual(result.configuration.parameters.min_observed);
      expect(r.ratio).toBeLessThan(result.configuration.parameters.max_ratio);
    });
    expect(result.ep_share).toBeGreaterThanOrEqual(0);
    expect(result.ep_share).toBeLessThanOrEqual(1);
  });

  it("shouldComputeTheEpShareFromEpDocumentsWhenSummarising", () => {
    const all = result.trend.filter((t) => t.year <= 2025);
    const expected = all.reduce((s, t) => s + t.ep_documents, 0) / all.reduce((s, t) => s + t.documents, 0);
    const shares = Object.values(periodEpShare(result)).filter((v): v is number => v !== null);
    expect(shares.length).toBeGreaterThan(0);
    shares.forEach((v) => expect(v).toBeLessThanOrEqual(1));
    expect(result.ep_share).toBeCloseTo(expected, 8);
  });

  it("shouldReadTrendShareAsPercentWhenDrawingTheChart", () => {
    result.trend.forEach((t) => {
      expect(t.share).toBeGreaterThanOrEqual(0);
      expect(t.share).toBeLessThanOrEqual(100);
    });
    expect(Math.max(...result.trend.map((t) => t.share))).toBeGreaterThan(1); // a fraction would never exceed 1
  });

  it("shouldNameTheLeaderOfTheLastTwoYearsWhenSummarising", () => {
    const recent = result.top_applicant_recent!;
    const lastTwo = recent.by_year.slice(-2).reduce((s, n) => s + n, 0);
    expect(lastTwo).toBeGreaterThan(0);
    expect(result.applicants[0].name).not.toBe(recent.name); // the all-years leader differs by construction
    expect(dominantApplicant(result)?.name ?? recent.name).toBe(recent.name);
  });

  it("shouldRenderEveryViewWhenGivenTheSample", async () => {
    for (const hash of ["#/t", "#/t/evolucion", "#/t/tema", "#/t/quien", "#/t/pistas"]) {
      window.location.hash = hash;
      const { container, unmount } = render(createElement(TopicMapPage, { load: async () => result }));
      await waitFor(() => expect(container.textContent!.length).toBeGreaterThan(0));
      const text = container.textContent!;
      [...result.neighbours, ...result.rare].forEach((r) => expect(text).not.toContain(r.subclass));
      expect(screen.queryByText(/NaN|undefined/)).toBeNull();
      unmount();
    }
  });
});
