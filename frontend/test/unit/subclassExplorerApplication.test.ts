import { describe, expect, it } from "vitest";
import { filterRows, pairDetail, pairRows, searchSubclasses, sortRows } from "../../src/main/application/subclassExplorer";
import type { OriginPairs } from "../../src/main/domain/whitespace";

const origin: OriginPairs = {
  origin: 2006,
  min_documents: 20,
  active: { A01B: 250, A01C: 196, G06N: 90, G06F: 500, H04L: 40 },
  pairs: {
    "A01B|A01C": { documents: 16, by_year: { "2000": 3, "2003": 13 }, first_year: 2000 },
    "A01B|G06F": { documents: 2, by_year: { "2005": 2 }, first_year: 2005 },
    "G06F|G06N": { documents: 30, by_year: { "2001": 10, "2004": 20 }, first_year: 2001 },
  },
};

describe("the subclass explorer", () => {
  it("shouldFindSubclassesByPartOfTheirSymbolIgnoringCaseWhenSearching", () => {
    expect(searchSubclasses(origin, "g06")).toEqual(["G06F", "G06N"]);
    expect(searchSubclasses(origin, "")).toEqual([]);
    expect(searchSubclasses(origin, "zzz")).toEqual([]);
  });

  it("shouldListEveryOtherActiveSubclassWithItsPairStateWhenAskedForARow", () => {
    const rows = pairRows(origin, "A01B");
    expect(rows.map((r) => r.symbol)).toEqual(["A01C", "G06F", "G06N", "H04L"]);
    expect(rows.find((r) => r.symbol === "A01C")).toEqual({ symbol: "A01C", documents: 196, seen: true, both: 16, firstYear: 2000 });
    expect(rows.find((r) => r.symbol === "G06N")).toEqual({ symbol: "G06N", documents: 90, seen: false, both: 0, firstYear: null });
  });

  it("shouldFindThePairWhicheverSubclassIsChosenFirstWhenTheKeyIsSortedInTheData", () => {
    expect(pairRows(origin, "G06N").find((r) => r.symbol === "G06F")?.both).toBe(30);
  });

  it("shouldFilterBySeenStateAndBySectionWhenFiltering", () => {
    const rows = pairRows(origin, "A01B");
    expect(filterRows(rows, { seen: "unseen", section: "all" }).map((r) => r.symbol)).toEqual(["G06N", "H04L"]);
    expect(filterRows(rows, { seen: "seen", section: "all" }).map((r) => r.symbol)).toEqual(["A01C", "G06F"]);
    expect(filterRows(rows, { seen: "all", section: "G" }).map((r) => r.symbol)).toEqual(["G06F", "G06N"]);
  });

  it("shouldSortBySymbolDocumentsOrDocumentsWithBothAndNeverByAnythingDerivedWhenSorting", () => {
    const rows = pairRows(origin, "A01B");
    expect(sortRows(rows, "symbol").map((r) => r.symbol)).toEqual(["A01C", "G06F", "G06N", "H04L"]);
    expect(sortRows(rows, "documents").map((r) => r.symbol)).toEqual(["G06F", "A01C", "G06N", "H04L"]);
    expect(sortRows(rows, "both").map((r) => r.symbol)).toEqual(["A01C", "G06F", "G06N", "H04L"]);
  });

  it("shouldBreakTiesBySymbolAndNotMutateTheInputWhenSorting", () => {
    const rows = pairRows(origin, "A01B");
    const copy = [...rows];
    sortRows(rows, "both");
    expect(rows).toEqual(copy);
    expect(sortRows(rows, "both").slice(2).map((r) => r.symbol)).toEqual(["G06N", "H04L"]);
  });

  it("shouldGiveTheCountsByYearInOrderAndTheirTotalWhenOpeningAPair", () => {
    const detail = pairDetail(origin, "A01C", "A01B");
    expect(detail).toEqual({ a: "A01B", b: "A01C", seen: true, documents: 16, firstYear: 2000, byYear: [{ year: 2000, count: 3 }, { year: 2003, count: 13 }] });
  });

  it("shouldReportAnUnseenPairWithoutYearsOrCountsWhenOpeningIt", () => {
    expect(pairDetail(origin, "A01B", "H04L")).toEqual({ a: "A01B", b: "H04L", seen: false, documents: 0, firstYear: null, byYear: [] });
  });
});
