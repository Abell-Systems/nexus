import type { UnobservedPairsResults } from "../domain/whitespace";

export type PairType = "all" | "expected";
export type PairSort = "symbol" | "docsA" | "docsB" | "expected";

export interface UnobservedRow {
  a: string;
  b: string;
  docsA: number;
  docsB: number;
  expected: number;
}

export interface PairScope {
  symbol: string | null;
  section: string;
  type: PairType;
  sort: PairSort;
}

const byText = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

export function searchSymbols(data: UnobservedPairsResults, query: string): string[] {
  const needle = query.trim().toUpperCase();
  return needle ? Object.keys(data.active).filter((s) => s.includes(needle)).sort(byText) : [];
}

export const sectionsOf = (data: UnobservedPairsResults): string[] => [...new Set(Object.keys(data.active).map((s) => s[0]))].sort(byText);

// With a subclass chosen, `section` narrows the other subclass; with only a section, a pair matches when either subclass is in it.
// Nothing is listed until a subclass or a section is chosen. Sorting by expected count is only on the user's explicit choice.
export function listPairs(data: UnobservedPairsResults, { symbol, section, type, sort }: PairScope): UnobservedRow[] {
  if (!symbol && !section) return [];
  const rows: UnobservedRow[] = [];
  for (const [a, partners] of Object.entries(data.pairs)) {
    for (const [b, expected] of Object.entries(partners)) {
      const inScope = symbol
        ? (a === symbol || b === symbol) && (!section || (a === symbol ? b : a).startsWith(section))
        : a.startsWith(section) || b.startsWith(section);
      if (!inScope || (type === "expected" && expected < data.e_min)) continue;
      rows.push({ a, b, docsA: data.active[a], docsB: data.active[b], expected });
    }
  }
  const tie = (x: UnobservedRow, y: UnobservedRow) => byText(x.a, y.a) || byText(x.b, y.b);
  const keys = { symbol: () => 0, docsA: (x: UnobservedRow, y: UnobservedRow) => y.docsA - x.docsA, docsB: (x: UnobservedRow, y: UnobservedRow) => y.docsB - x.docsB, expected: (x: UnobservedRow, y: UnobservedRow) => y.expected - x.expected };
  return rows.sort((x, y) => keys[sort](x, y) || tie(x, y));
}
