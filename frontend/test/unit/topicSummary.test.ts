import { describe, expect, it } from "vitest";
import type { TopicMapResult } from "../../src/main/domain/topicMap";
import {
  dominantApplicant, evolutionSentence, formatNumber, peakYears, periodAverages, periodEpShare,
  summarySentence, visibleAndFolded,
} from "../../src/main/application/topicSummary";

// rows: [year, documents, ep_documents]
function make(
  rows: [number, number, number][],
  applicant: { name: string; by_year: number[] } | null = null,
): TopicMapResult {
  return {
    topic: { key: "t", name: "Tema", noun: "cosas", joined: "con cosas" },
    total_documents: rows.reduce((s, [, d]) => s + d, 0),
    years: rows.map(([y]) => y),
    trend: rows.map(([year, documents, ep_documents]) => ({ year, documents, share: 1, ep_documents })),
    top_applicant_recent: applicant,
  } as unknown as TopicMapResult;
}

// 2000-2009: 10 docs each (2 EP); 2010 absent; 2011: 20 (10 EP), 2012: 40 (10 EP); 2024: 60 (6 EP); 2025: 40 (4 EP)
const base: [number, number, number][] = [
  ...[2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009].map((y): [number, number, number] => [y, 10, 2]),
  [2011, 20, 10], [2012, 40, 10], [2024, 60, 6], [2025, 40, 4],
];
const withApplicant = (n2024: number, n2025: number) =>
  make(base, { name: "Acme", by_year: [...Array(12).fill(0), n2024, n2025] });
const noDocs = make([[2000, 0, 0], [2001, 0, 0], [2024, 0, 0], [2025, 0, 0]]);
const noRecent = make(base.slice(0, -2));

describe("topicSummary", () => {
  it("shouldIgnoreTheYearWithoutDocumentsWhenAveraging", () => {
    expect(periodAverages(make(base))).toEqual({ early: 10, middle: 30, recent: 50 });
  });

  it("shouldGiveNullForAPeriodWithoutRows", () => {
    expect(periodAverages(noRecent).recent).toBeNull();
    expect(periodEpShare(noRecent).recent).toBeNull();
    expect(evolutionSentence(noRecent)).not.toContain("2024");
    expect(summarySentence(noRecent)).not.toContain("2024");
  });

  it("shouldMentionTheEpTranslationShareOfEachPeriod", () => {
    expect(periodEpShare(make(base))).toEqual({ early: 0.2, middle: 20 / 60, recent: 0.1 });
    const s = evolutionSentence(make(base));
    expect(s).toContain("20 %");
    expect(s).toContain("33 %");
    expect(s).toContain("10 %");
  });

  it("shouldNameAllTiedPeakYears", () => {
    expect(peakYears(make([[2000, 5, 0], [2001, 9, 0], [2002, 9, 0], [2003, 1, 0]]))).toEqual([2001, 2002]);
    expect(evolutionSentence(make([[2000, 5, 0], [2001, 9, 0], [2002, 9, 0]]))).toContain("2001 y 2002");
    expect(evolutionSentence(make(base))).toContain("fue 2024");
  });

  it("shouldSayNothingAboutPeaksWhenTheTopicHasNoDocuments", () => {
    expect(peakYears(noDocs)).toEqual([]);
    expect(periodEpShare(noDocs)).toEqual({ early: null, middle: null, recent: null });
    expect(evolutionSentence(noDocs)).toBe("No hay documentos de este tema desde 2000.");
    expect(summarySentence(noDocs)).toBe("No hay documentos de este tema desde 2000.");
  });

  it("shouldReportADominantApplicantWhenItIsAtLeast30Percent", () => {
    // last two years: 100 documents; 30 -> exactly 0.3
    const r = withApplicant(18, 12);
    expect(dominantApplicant(r)).toEqual({ name: "Acme", share: 0.3 });
    expect(evolutionSentence(r)).toContain("Acme");
    expect(evolutionSentence(r)).toContain("30 %");
    expect(evolutionSentence(r)).toContain("35 al año"); // (100-30)/2
    expect(summarySentence(r)).toContain("Acme");
    expect(summarySentence(r)).toContain("30 %");
  });

  it("shouldNotReportItWhenItIs29Percent", () => {
    const r = withApplicant(17, 12);
    expect(dominantApplicant(r)).toBeNull();
    expect(evolutionSentence(r)).not.toContain("Acme");
    expect(evolutionSentence(r)).toContain("Ningún solicitante domina");
    expect(summarySentence(r)).not.toContain("Acme");
  });

  it("shouldNameTheRecentLeaderAndStateTheRealPercentage", () => {
    // result already carries the recent leader (not the overall one)
    const r = withApplicant(40, 20);
    expect(dominantApplicant(r)?.share).toBeCloseTo(0.6);
    expect(summarySentence(r)).toContain("60 %");
    const r2 = withApplicant(30, 10); // 40 %: must not claim a majority
    expect(summarySentence(r2)).toContain("40 %");
    expect(summarySentence(r2)).not.toContain("la mitad");
  });

  it("shouldReturnNullWhenThereIsNoRecentApplicantOrNoRecentDocuments", () => {
    expect(dominantApplicant(make(base))).toBeNull();
    expect(dominantApplicant(make([[2024, 0, 0], [2025, 0, 0]], { name: "A", by_year: [0, 0] }))).toBeNull();
  });

  it("shouldNeverUseTheWordsCreceOrDecrece", () => {
    const words = /crece|decrece|crecimiento|aumento|disminuye/i;
    for (const r of [make(base), withApplicant(18, 12), withApplicant(17, 12), noDocs, noRecent,
      make([[2000, 1, 0], [2001, 50, 0]]), make([[2000, 50, 0], [2001, 1, 0]])]) {
      expect(evolutionSentence(r)).not.toMatch(words);
      expect(summarySentence(r)).not.toMatch(words);
    }
  });

  it("shouldDescribeTheTotalAndAveragesInTheSummary", () => {
    expect(summarySentence(make(base))).toBe(
      "Desde 2000 hay 260 documentos de este tema. De media, 50 al año en 2024–2025 y 30 al año en 2011–2023.",
    );
  });

  it("shouldFormatThousandsWithADot", () => {
    expect(formatNumber(1046)).toBe("1.046");
    expect(formatNumber(5676)).toBe("5.676");
    expect(formatNumber(999)).toBe("999");
    expect(formatNumber(1234567)).toBe("1.234.567");
  });

  it("shouldFoldTheItemsBeyondFive", () => {
    expect(visibleAndFolded([1, 2, 3, 4, 5, 6, 7])).toEqual({ visible: [1, 2, 3, 4, 5], folded: [6, 7] });
    expect(visibleAndFolded([1, 2, 3])).toEqual({ visible: [1, 2, 3], folded: [] });
    expect(visibleAndFolded([1, 2, 3], 2)).toEqual({ visible: [1, 2], folded: [3] });
  });
});
