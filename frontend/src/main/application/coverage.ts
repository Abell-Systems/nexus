import type { ExposureResults, KindGroup } from "../domain/whitespace";

export interface CoverageBar {
  year: number;
  inventory: number;
  present: number;
  absentY: number;
  absentRest: number;
  absentShare: number;
}

const GROUPS: readonly KindGroup[] = ["ep_translation", "kind_y", "other"];

/** One bar per year, straight from the exposure table: present, absent of kind Y, absent of the other kinds. */
export function coverageBars(results: ExposureResults): CoverageBar[] {
  return Object.entries(results.exposure.by_year)
    .map(([year, cells]) => {
      const inventory = GROUPS.reduce((sum, group) => sum + cells[group].inventory, 0);
      const present = GROUPS.reduce((sum, group) => sum + cells[group].present, 0);
      const absentY = cells.kind_y.absent;
      const absentRest = cells.ep_translation.absent + cells.other.absent;
      return { year: Number(year), inventory, present, absentY, absentRest, absentShare: inventory ? (100 * (absentY + absentRest)) / inventory : 0 };
    })
    .sort((a, b) => a.year - b.year);
}

/** Years in which the inventory lists kind Y publications and the corpus has none, while it has other kinds (a whole missing year is reported apart). */
export function yearsWhereEveryKindYIsAbsent(results: ExposureResults): number[] {
  return Object.entries(results.exposure.by_year)
    .filter(([, cells]) => cells.kind_y.inventory > 0 && cells.kind_y.present === 0 && GROUPS.some((group) => cells[group].present > 0))
    .map(([year]) => Number(year))
    .sort((a, b) => a - b);
}

/** The y positions of a bar chart: one scale for every bar, from zero to the tallest inventory. */
export function barScale(bars: readonly CoverageBar[], height: number): (value: number) => number {
  const peak = Math.max(...bars.map((bar) => bar.inventory), 1);
  return (value) => (value / peak) * height;
}
