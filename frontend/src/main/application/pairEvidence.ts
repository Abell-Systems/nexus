import type { UnobservedPairsResults } from "../domain/whitespace";
import { reconstructExpected, type ReconstructedExpected } from "./expectedTerms";

export interface YearPoint {
  year: number;
  /** null: the corpus has no document at all in this year (2010), which is a gap and never a zero. */
  countA: number | null;
  countB: number | null;
}

export interface PairEvidence {
  a: string;
  b: string;
  documentsA: number;
  documentsB: number;
  stored: number;
  years: YearPoint[];
  maxCount: number;
  reconstruction: ReconstructedExpected;
}

// Everything the sheet shows comes from the verified result already in memory; nothing here feeds a list, a filter or a sort.
export function buildEvidence(data: UnobservedPairsResults, a: string, b: string): PairEvidence | null {
  const stored = data.pairs[a]?.[b];
  const byYearA = data.documents_by_year[a];
  const byYearB = data.documents_by_year[b];
  if (stored === undefined || !byYearA || !byYearB) return null;
  const observed = Object.keys(data.documents_per_year).map(Number);
  const first = Math.min(...observed);
  const last = Math.max(...observed);
  const years: YearPoint[] = [];
  for (let year = first; year <= last; year++) {
    const inCorpus = String(year) in data.documents_per_year;
    years.push({ year, countA: inCorpus ? (byYearA[year] ?? 0) : null, countB: inCorpus ? (byYearB[year] ?? 0) : null });
  }
  const maxCount = Math.max(1, ...years.flatMap((y) => [y.countA ?? 0, y.countB ?? 0]));
  return {
    a,
    b,
    documentsA: data.active[a],
    documentsB: data.active[b],
    stored,
    years,
    maxCount,
    reconstruction: reconstructExpected(byYearA, byYearB, data.documents_per_year, stored),
  };
}
