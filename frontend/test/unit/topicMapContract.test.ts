import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import { TopicMapPage } from "../../src/main/components/TopicMap/TopicMapPage";
import { dominantApplicant, periodEpShare } from "../../src/main/application/topicSummary";
import { views } from "../../src/main/application/topicMapStrings";
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
    const isStr = (v: unknown) => typeof v === "string" && v.length > 0;
    const isCount = (v: unknown) => Number.isInteger(v) && (v as number) >= 0;
    const isNum = (v: unknown) => typeof v === "number" && Number.isFinite(v);
    const all = (vs: unknown[], check: (v: unknown) => boolean) => vs.every(check);
    const p = result.configuration.parameters;
    expect([result.schema, result.configuration.id, p.schema, p.definition_id, p.applicant_rules_id, p.unit].every(isStr)).toBe(true);
    expect(all([p.min_observed, p.min_expected, p.max_ratio], isNum)).toBe(true);
    expect(typeof result.names_reviewed).toBe("boolean");
    expect(all(result.unreviewed, isStr)).toBe(true);
    expect(result.schema).toBe("topic-map/1");
    expect(isStr(result.corpus.source_id)).toBe(true);
    expect(Object.values(result.corpus.files).every((h) => /^[0-9a-f]{64}$/.test(h))).toBe(true);
    expect(Object.keys(result.corpus.files).length).toBeGreaterThan(0);
    expect(Object.values(result.topic).every(isStr)).toBe(true);
    expect(isCount(result.total_documents) && isCount(result.corpus_documents)).toBe(true);
    expect(result.total_documents).toBeLessThanOrEqual(result.corpus_documents);
    expect(all(result.years, isCount)).toBe(true);
    expect(result.years).toEqual([...result.years].sort((a, b) => a - b));
    expect(new Set(result.years).size).toBe(result.years.length);
    expect(result.years).not.toContain(2010);
    expect(result.trend.map((t) => t.year)).toEqual(result.years);
    result.trend.forEach((t) => {
      expect(all([t.documents, t.ep_documents], isCount)).toBe(true);
      expect(t.ep_documents).toBeLessThanOrEqual(t.documents);
      expect(isNum(t.share)).toBe(true);
    });
    expect(result.trend.reduce((s, t) => s + t.documents, 0)).toBe(result.total_documents);
    expect(isNum(result.ep_share)).toBe(true);
    const recent = result.top_applicant_recent!;
    expect(isStr(recent.name)).toBe(true);
    expect(recent.by_year).toHaveLength(result.years.length);
    expect(all(recent.by_year, isCount)).toBe(true);
    result.subareas.forEach((a) => {
      expect([a.key, a.name, a.description].every(isStr)).toBe(true);
      expect(isCount(a.documents)).toBe(true);
      expect(a.series).toHaveLength(result.years.length);
      expect(all(a.series, isCount)).toBe(true);
    });
    result.neighbours.forEach((n) => expect(isStr(n.subclass) && isStr(n.name) && isCount(n.documents)).toBe(true));
    expect(result.neighbours.map((n) => n.documents)).toEqual([...result.neighbours.map((n) => n.documents)].sort((a, b) => b - a));
    result.rare.forEach((r) => {
      expect(isStr(r.subclass) && isStr(r.name) && isCount(r.observed) && isNum(r.expected) && isNum(r.ratio)).toBe(true);
      expect(r.observed).toBeGreaterThanOrEqual(p.min_observed);
      expect(r.expected).toBeGreaterThanOrEqual(p.min_expected);
      expect(r.ratio).toBeLessThan(p.max_ratio);
    });
    result.applicants.forEach((a) => {
      expect(isStr(a.name) && isCount(a.documents)).toBe(true);
      expect(a.originals.length).toBeGreaterThan(0);
      expect(all(a.originals, isStr)).toBe(true);
    });
    expect(result.applicants.map((a) => a.documents)).toEqual([...result.applicants.map((a) => a.documents)].sort((a, b) => b - a));
    expect(result.ep_share).toBeGreaterThanOrEqual(0);
    expect(result.ep_share).toBeLessThanOrEqual(1);
  });

  it("shouldComputeTheEpShareOfEachPeriodFromEpDocumentsWhenSummarising", () => {
    const expectedFor = (t: TopicMapResult, from: number, to: number) => {
      const rows = t.trend.filter((r) => r.year >= from && r.year <= to);
      const docs = rows.reduce((s, r) => s + r.documents, 0);
      return docs ? rows.reduce((s, r) => s + r.ep_documents, 0) / docs : null;
    };
    const periods = { early: [2000, 2009], middle: [2011, 2023], recent: [2024, 2025] } as const;
    const check = (t: TopicMapResult) =>
      Object.entries(periodEpShare(t)).forEach(([name, value]) => {
        const [from, to] = periods[name as keyof typeof periods];
        expect(value).toBe(expectedFor(t, from, to));
      });
    check(result);
    expect(periodEpShare(result)).toEqual({ early: 1 / 553, middle: 0, recent: null }); // by hand from the sample: 1 EP unit of 553 documents
    const changed = structuredClone(result); // sensitivity: a different ep_documents must change the answer
    changed.trend[0].ep_documents = 26;
    check(changed);
    expect(periodEpShare(changed).early).toBe(27 / 553);
    expect(result.ep_share).toBeCloseTo(result.trend.reduce((s, t) => s + t.ep_documents, 0) / result.total_documents, 8);
  });

  it("shouldGiveEveryYearTheShareOfItsCorpusYearAsAPercentWhenDrawingTheChart", () => {
    expect(result.trend.map((t) => t.share)).toEqual([100, 50, 0, 50, 100]); // reviewed against the synthetic inputs: topic units / corpus units per year
    // the corpus year size n is not in the payload; it is recovered from share and must be a whole number of units
    const sizes = result.trend.map((t) => (t.documents ? (100 * t.documents) / t.share : null));
    expect(sizes).toEqual([52, 2, null, 1000, 1]);
    const known = sizes.reduce((s: number, n) => s + (n ?? 0), 0);
    expect(known).toBeLessThanOrEqual(result.corpus_documents); // the year without topic units holds the rest
    expect(result.corpus_documents - known).toBe(1);
  });

  it("shouldNameTheLeaderOfTheLastTwoYearsWhenSummarising", () => {
    const recent = result.top_applicant_recent!;
    expect(recent.name).toBe("Zeta");
    expect(result.applicants[0].name).not.toBe(recent.name); // the all-years leader differs by construction
    expect(dominantApplicant(result)).toBeNull(); // 1 of 501 documents in the last two years: below the dominance threshold
    const dominant = structuredClone(result);
    dominant.top_applicant_recent!.by_year = [900, 0, 0, 1, 60]; // the old 900 must not count: only the last two years do
    dominant.trend[3].documents = 100;
    dominant.trend[4].documents = 100;
    const found = dominantApplicant(dominant);
    expect(found).not.toBeNull();
    expect(found!.name).toBe(recent.name);
    expect(found!.recentDocuments).toBe(61);
    expect(found!.share).toBeCloseTo(61 / 200, 10);
  });

  it("shouldRenderEachViewWithItsOwnHeadingWhenGivenTheSample", async () => {
    const routes = [
      ["#/baterias", null],
      ["#/baterias/evolucion", views.evolucion],
      ["#/baterias/tema", views.tema],
      ["#/baterias/quien", views.quien],
      ["#/baterias/pistas", views.pistas],
    ] as const;
    for (const [hash, heading] of routes) {
      window.location.hash = hash;
      const { container, unmount } = render(createElement(TopicMapPage, { load: async () => result }));
      if (heading) {
        expect((await screen.findByRole("heading", { level: 1, name: heading })).textContent).toBe(heading);
        Object.values(views).filter((v) => v !== heading).forEach((other) => expect(screen.queryByRole("heading", { level: 1, name: other })).toBeNull());
      } else {
        for (const v of Object.values(views)) expect(await screen.findByRole("link", { name: v })).toBeTruthy(); // the summary offers the four views
      }
      const text = container.textContent!;
      expect(text).not.toMatch(/NaN|undefined|null|\[object/);
      // the synthetic plain names embed their code ("Nombre Q01Q"), so the names (and applicant names) are removed first: a bare code would be left over
      const shown = [...result.neighbours, ...result.rare, ...result.applicants].map((x) => x.name);
      const bare = shown.reduce((t, name) => t.replaceAll(name, ""), text);
      [...result.neighbours, ...result.rare].forEach((r) => expect(bare).not.toContain(r.subclass));
      unmount();
    }
  });
});
