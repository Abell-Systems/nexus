import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { reconstructExpected } from "../../src/main/application/expectedTerms";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");

// The fixture of the Python test: A01B and B01B, 2000 and 2002, 4 documents each year, 2001 has no documents.
const perYear = { "2000": 4, "2002": 4 };
const a = { "2000": 2, "2002": 1 };
const b = { "2000": 2, "2002": 1 };

describe("reconstructExpected", () => {
  it("shouldReconstructTheHandComputedExpectedCountWhenAYearHasNoDocuments", () => {
    const result = reconstructExpected(a, b, perYear, 1.25);
    expect(result.terms.map((t) => [t.year, t.term])).toEqual([[2000, 1], [2002, 0.25]]);
    expect(result.sum).toBe(1.25);
    expect(result.concordant).toBe(true);
  });

  it("shouldNotListAYearWithoutDocumentsOrAYearWhereOneSubclassHasNone", () => {
    const result = reconstructExpected({ "2000": 2 }, { "2002": 1 }, { "2000": 4, "2001": 0, "2002": 4 }, 0);
    expect(result.terms).toEqual([]);
    expect(result.concordant).toBe(true);
  });

  it("shouldSumTheTermsInAscendingYearOrderWhateverTheKeyOrder", () => {
    const shuffled = { "2002": 4, "2000": 4 };
    expect(reconstructExpected(a, b, shuffled, 1.25).terms.map((t) => t.year)).toEqual([2000, 2002]);
  });

  it("shouldShowADiscrepancyWithoutCorrectingTheStoredValueWhenTheyDifferByOneUnitOfTheLastDecimal", () => {
    const result = reconstructExpected(a, b, perYear, 1.250000001);
    expect(result.concordant).toBe(false);
    expect(result.rounded).toBe(1.25);
  });
});

describe("the stored result", () => {
  const result = JSON.parse(readFileSync(join(root, "docs", "whitespace", "oepm-unobserved-pairs-results.json"), "utf8"));

  it("shouldBeConcordantForEveryUnobservedPairWithTheProcedureOfTheSheet", () => {
    let pairs = 0;
    const discrepancies: string[] = [];
    for (const [first, row] of Object.entries<Record<string, number>>(result.pairs)) {
      for (const [second, stored] of Object.entries(row)) {
        pairs++;
        const r = reconstructExpected(result.documents_by_year[first], result.documents_by_year[second], result.documents_per_year, stored);
        if (!r.concordant && discrepancies.length < 5) discrepancies.push(`${first}|${second} stored=${stored} sum=${r.sum}`);
      }
    }
    expect(pairs).toBe(result.counts.unobserved);
    expect(discrepancies).toEqual([]);
  });
});
