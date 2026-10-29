import type { TopicMapResult } from "../domain/topicMap";
import * as S from "./topicMapStrings";

type Period = "early" | "middle" | "recent";
type ByPeriod<T> = Record<Period, T | null>;

const RANGES: Record<Period, [number, number]> = { early: [2000, 2009], middle: [2011, 2023], recent: [2024, 2025] };
const DOMINANCE = 0.3;

const rowsOf = (r: TopicMapResult, p: Period) =>
  r.trend.filter((t) => t.year >= RANGES[p][0] && t.year <= RANGES[p][1]);
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
function perPeriod<T>(r: TopicMapResult, f: (rows: TopicMapResult["trend"]) => T | null): ByPeriod<T> {
  const rows = (p: Period) => rowsOf(r, p);
  return { early: f(rows("early")), middle: f(rows("middle")), recent: f(rows("recent")) };
}

export const periodAverages = (r: TopicMapResult) =>
  perPeriod(r, (rows) => (rows.length ? sum(rows.map((t) => t.documents)) / rows.length : null));

export const periodEpShare = (r: TopicMapResult) =>
  perPeriod(r, (rows) => {
    const docs = sum(rows.map((t) => t.documents));
    return docs ? sum(rows.map((t) => t.ep_documents)) / docs : null;
  });

export function peakYears(r: TopicMapResult): number[] {
  const max = Math.max(0, ...r.trend.map((t) => t.documents));
  return max ? r.trend.filter((t) => t.documents === max).map((t) => t.year).sort((a, b) => a - b) : [];
}

const lastTwo = (r: TopicMapResult) => r.trend.slice(-2);
const yearsLabel = (r: TopicMapResult) => lastTwo(r).map((t) => t.year).join(S.and);

export function dominantApplicant(r: TopicMapResult): { name: string; share: number; recentDocuments: number } | null {
  const a = r.top_applicant_recent;
  const denominator = sum(lastTwo(r).map((t) => t.documents));
  if (!a || !denominator) return null;
  const recentDocuments = sum(a.by_year.slice(-2));
  const share = recentDocuments / denominator;
  return share >= DOMINANCE ? { name: a.name, share, recentDocuments } : null;
}

export function formatNumber(n: number): string {
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

const whole = (n: number) => formatNumber(n);
const docsPerYear = (avg: number) => {
  const n = Math.round(avg);
  return S.docsPerYear(whole(avg), avg > 0 && avg < 1 ? "less" : n === 0 ? "zero" : n === 1 ? "one" : "many");
};
const pct = (f: number) => {
  const n = Math.round(f * 100);
  return S.share(String(n), f > 0 && n < 1 ? "less" : f < 1 && n >= 100 ? "almost" : "exact");
};
const hasNoDocuments = (r: TopicMapResult) => sum(r.trend.map((t) => t.documents)) === 0;

function dominantClause(r: TopicMapResult, withoutIt: boolean): string | null {
  const d = dominantApplicant(r);
  if (!d) return null;
  if (!withoutIt) return S.dominantSummary(d.name, pct(d.share), yearsLabel(r));
  const rows = lastTwo(r);
  const rest = Math.max(0, sum(rows.map((t) => t.documents)) - d.recentDocuments) / rows.length;
  return S.dominantEvolution(d.name, pct(d.share), yearsLabel(r), docsPerYear(rest));
}

export function evolutionSentence(r: TopicMapResult): string {
  if (hasNoDocuments(r)) return S.noDocuments;
  const avg = periodAverages(r);
  const ep = periodEpShare(r);
  const parts = (["early", "middle", "recent"] as const).flatMap((p) =>
    avg[p] === null ? [] : [S.periodAverage(S.PERIODS[p], docsPerYear(avg[p]), ep[p] === null ? null : S.epShare(pct(ep[p])))],
  );
  if (!parts.length) return S.noPeriodData;
  const peaks = peakYears(r).map(String);
  const peak = peaks.length === 1
    ? S.peakOne(peaks[0])
    : S.peakMany(`${peaks.slice(0, -1).join(", ")}${S.and}${peaks[peaks.length - 1]}`);
  const noRecent = sum(lastTwo(r).map((t) => t.documents)) === 0;
  const dominance = noRecent ? S.noRecentDocuments(yearsLabel(r)) : dominantClause(r, true) ?? S.noDominant(yearsLabel(r));
  const first = parts.join("; ");
  return `${first[0].toUpperCase()}${first.slice(1)}. ${peak}. ${dominance}.`;
}

export function summarySentence(r: TopicMapResult): string {
  if (hasNoDocuments(r)) return S.noDocuments;
  const { middle, recent } = periodAverages(r);
  const averages = recent !== null && middle !== null
    ? S.averages(docsPerYear(recent), docsPerYear(middle))
    : recent !== null ? S.averageOne(docsPerYear(recent), S.PERIODS.recent)
    : middle !== null ? S.averageOne(docsPerYear(middle), S.PERIODS.middle)
    : null;
  return [S.total(whole(r.total_documents), r.total_documents === 1), averages, dominantClause(r, false)]
    .filter((x): x is string => x !== null)
    .join(". ") + ".";
}

export function visibleAndFolded<T>(items: T[], limit = 5): { visible: T[]; folded: T[] } {
  return { visible: items.slice(0, limit), folded: items.slice(limit) };
}
