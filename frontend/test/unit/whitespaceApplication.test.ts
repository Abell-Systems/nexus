import { describe, expect, it } from "vitest";
import { chooseScreen } from "../../src/main/application/screen";
import { barScale, coverageBars, yearsWhereEveryKindYIsAbsent } from "../../src/main/application/coverage";
import { commonPeak, level, mapCells } from "../../src/main/application/sectionMap";
import { sensitivityRows } from "../../src/main/application/sensitivity";
import type { ExposureResults, SectionDensity, SensitivityResults, YearGroup } from "../../src/main/domain/whitespace";
import { whitespaceData } from "../../src/main/infrastructure/whitespaceData";

const group = (inventory: number, absent: number): YearGroup => ({ inventory, present: inventory - absent, absent, absent_share_percent: 0 });

const exposure = {
  authority_file: { name: "a.zip", sha256: "x" },
  exposure: {
    inventory_publications: 0,
    corpus_publications: 0,
    accumulated_up_to_origin: {},
    by_year: {
      "2001": { ep_translation: group(10, 1), kind_y: group(4, 4), other: group(6, 0), corpus_keys_not_in_inventory: 0 },
      "2000": { ep_translation: group(8, 0), kind_y: group(2, 2), other: group(5, 1), corpus_keys_not_in_inventory: 0 },
      "2002": { ep_translation: group(9, 0), kind_y: group(3, 0), other: group(4, 0), corpus_keys_not_in_inventory: 0 },
    },
  },
} satisfies ExposureResults;

describe("coverage", () => {
  it("shouldSplitEachYearIntoPresentAndAbsentByKindGroupWhenBuildingBars", () => {
    const [first, second] = coverageBars(exposure);
    expect(first).toMatchObject({ year: 2000, inventory: 15, present: 12, absentY: 2, absentRest: 1 });
    expect(second).toMatchObject({ year: 2001, inventory: 20, present: 15, absentY: 4, absentRest: 1 });
    expect(coverageBars(exposure).map((bar) => bar.year)).toEqual([2000, 2001, 2002]);
  });

  it("shouldListYearsWithoutAnyKindYPublicationAndLeaveAWholeMissingYearApartWhenSearchingTotalAbsence", () => {
    expect(yearsWhereEveryKindYIsAbsent(exposure)).toEqual([2000, 2001]);
    expect(yearsWhereEveryKindYIsAbsent(whitespaceData.exposure)).toEqual([2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009]); // 2010 is wholly missing, reported apart
  });

  it("shouldUseOneScaleForEveryBarWhenDrawingTheChart", () => {
    const scale = barScale(coverageBars(exposure), 100);
    expect(scale(20)).toBe(100);
    expect(scale(10)).toBe(50);
  });

  it("shouldReproduceTheVersionedTotalsFromTheRealResults", () => {
    const bars = coverageBars(whitespaceData.exposure);
    expect(bars).toHaveLength(26);
    expect(bars.find((bar) => bar.year === 2010)).toMatchObject({ present: 0, inventory: 25849 });
  });
});

const map = (origin: number, percents: Record<string, number>): SectionDensity => ({
  origin,
  min_documents: 20,
  active_subclasses: 3,
  active_subclasses_by_section: { A: 2, B: 1 },
  seen_pairs: 0,
  cells: Object.fromEntries(Object.entries(percents).map(([k, v]) => [k, { possible_pairs: 100, seen_pairs: v, seen_percent: v }])),
});

describe("section map", () => {
  const first = map(2006, { AA: 10, AB: 20, BB: 30 });
  const second = map(2022, { AA: 40, AB: 50, BB: 60 });

  it("shouldTakeTheLargestShareOfAllMapsAsTheCommonPeakWhenComparingThem", () => {
    expect(commonPeak([first, second])).toBe(60);
  });

  it("shouldGiveTheSameLevelToTheSameShareInBothMapsWhenTheScaleIsCommon", () => {
    const peak = commonPeak([first, second]);
    expect(level(30, peak)).toBe(mapCells(first, peak).rows[1][1].level);
    expect(level(30, peak)).toBe(level(30, peak));
    expect(mapCells(first, peak).rows[1][1].level).toBeLessThan(mapCells(second, peak).rows[1][1].level);
  });

  it("shouldReadASymmetricMatrixFromSortedSectionPairsWhenBuildingCells", () => {
    const { sections, rows } = mapCells(first, 60);
    expect(sections).toEqual(["A", "B"]);
    expect(rows[0][1].seenPercent).toBe(20);
    expect(rows[1][0].seenPercent).toBe(20);
  });
});

describe("sensitivity", () => {
  it("shouldGiveTheRangeOfRemovingOneHistoryYearWhenBuildingRows", () => {
    const quantities = (positives: number) => ({ active_subclasses: 1, candidate_pairs: 1, positives, positive_rate_percent: 1 });
    const results: SensitivityResults = {
      sensitivity: {
        "2003": {
          "S-A": quantities(100),
          "S-B1": { "2000": quantities(120), "2001": quantities(150) },
          "S-B2": quantities(130),
          "S-C": { replications: 200, positives: { mean: 99, "p2.5": 95, "p97.5": 101 } },
        },
      },
    };
    expect(sensitivityRows(results)).toEqual([
      { origin: "2003", observed: 100, removedYearMin: 120, removedYearMax: 150, shortenedHistory: 130, simulatedLow: 95, simulatedHigh: 101 },
    ]);
  });
});

describe("screen choice", () => {
  it("shouldShowTheStudyOnTheFrontPageAndKeepTheMatcherOnItsOwnAddressAndSharedLinks", () => {
    expect(chooseScreen("/", "")).toBe("whitespace");
    expect(chooseScreen("/matches", "")).toBe("matcher");
    expect(chooseScreen("/", "?demanda=abc")).toBe("matcher");
    expect(chooseScreen("/matches", "?demanda=abc")).toBe("matcher");
  });
});
