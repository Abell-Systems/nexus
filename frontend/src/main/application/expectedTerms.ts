export const STORED_DECIMALS = 9;

export interface YearTerm {
  year: number;
  countA: number;
  countB: number;
  total: number;
  term: number;
}

export interface ReconstructedExpected {
  terms: YearTerm[];
  sum: number;
  rounded: number;
  concordant: boolean;
}

type ByYear = Readonly<Record<string, number>>;

// Presentation arithmetic of the evidence sheet (contract section 5, rules of the per-year terms). The stored expected count stays the
// reference: nothing here feeds a filter, a sort or a label. One criterion and no tolerance: each term is (n_i * n_j) / N(y), the terms are
// summed in ascending order of year, the sum is rounded with Number(sum.toFixed(9)) and compared with the stored value by ===.
// Only the years of the corpus (those with documents) are visited, so a missing year such as 2010 never appears as a zero; a year in
// which one of the two subclasses has no documents contributes nothing and is not listed.
export function reconstructExpected(byYearA: ByYear, byYearB: ByYear, documentsPerYear: ByYear, stored: number): ReconstructedExpected {
  const terms: YearTerm[] = [];
  let sum = 0;
  for (const year of Object.keys(documentsPerYear).map(Number).sort((a, b) => a - b)) {
    const countA = byYearA[year] ?? 0;
    const countB = byYearB[year] ?? 0;
    if (!countA || !countB) continue;
    const total = documentsPerYear[year];
    const term = (countA * countB) / total;
    terms.push({ year, countA, countB, total, term });
    sum += term;
  }
  const rounded = Number(sum.toFixed(STORED_DECIMALS));
  return { terms, sum, rounded, concordant: rounded === stored };
}
