import type { OriginPairs } from "../domain/whitespace";

export type SeenFilter = "all" | "seen" | "unseen";
export type SortKey = "symbol" | "documents" | "both";

export interface PairRow {
  symbol: string;
  documents: number;
  seen: boolean;
  both: number;
  firstYear: number | null;
}

export interface PairDetail {
  a: string;
  b: string;
  seen: boolean;
  documents: number;
  firstYear: number | null;
  byYear: { year: number; count: number }[];
}

const byText = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const key = (a: string, b: string) => (a < b ? `${a}|${b}` : `${b}|${a}`);

export function searchSubclasses(origin: OriginPairs, query: string): string[] {
  const needle = query.trim().toUpperCase();
  return needle ? Object.keys(origin.active).filter((s) => s.includes(needle)).sort(byText) : [];
}

export function pairRows(origin: OriginPairs, symbol: string): PairRow[] {
  return Object.entries(origin.active)
    .filter(([other]) => other !== symbol)
    .map(([other, documents]) => {
      const pair = origin.pairs[key(symbol, other)];
      return { symbol: other, documents, seen: pair !== undefined, both: pair?.documents ?? 0, firstYear: pair?.first_year ?? null };
    })
    .sort((x, y) => byText(x.symbol, y.symbol));
}

export function filterRows(rows: readonly PairRow[], filter: { seen: SeenFilter; section: string }): PairRow[] {
  return rows.filter(
    (row) =>
      (filter.seen === "all" || row.seen === (filter.seen === "seen")) && (filter.section === "all" || row.symbol.startsWith(filter.section)),
  );
}

/** Symbol ascending; documents and documents with both descending, ties by symbol. No derived measure is offered. */
export function sortRows(rows: readonly PairRow[], sortKey: SortKey): PairRow[] {
  const copy = [...rows].sort((x, y) => byText(x.symbol, y.symbol));
  return sortKey === "symbol" ? copy : copy.sort((x, y) => (sortKey === "documents" ? y.documents - x.documents : y.both - x.both));
}

export function pairDetail(origin: OriginPairs, x: string, y: string): PairDetail {
  const [a, b] = x < y ? [x, y] : [y, x];
  const pair = origin.pairs[`${a}|${b}`];
  return {
    a,
    b,
    seen: pair !== undefined,
    documents: pair?.documents ?? 0,
    firstYear: pair?.first_year ?? null,
    byYear: Object.entries(pair?.by_year ?? {})
      .map(([year, count]) => ({ year: Number(year), count }))
      .sort((p, q) => p.year - q.year),
  };
}
