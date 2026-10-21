import type { SectionDensity } from "../domain/whitespace";

export const LEVELS = 5;

/** One scale for every map that is compared: zero to the largest share of any of them. */
export function commonPeak(maps: readonly SectionDensity[]): number {
  return Math.max(...maps.flatMap((map) => Object.values(map.cells).map((cell) => cell.seen_percent)), 0);
}

export function level(seenPercent: number, peak: number): number {
  return peak > 0 ? Math.round((LEVELS * seenPercent) / peak) : 0;
}

export interface MapCell {
  row: string;
  column: string;
  seenPercent: number;
  seenPairs: number;
  possiblePairs: number;
  level: number;
}

/** The symmetric matrix of a map: cells are keyed by the sorted pair of sections, as in the results. */
export function mapCells(map: SectionDensity, peak: number): { sections: string[]; rows: MapCell[][] } {
  const sections = Object.keys(map.active_subclasses_by_section).sort();
  const rows = sections.map((row) =>
    sections.map((column) => {
      const cell = map.cells[row <= column ? row + column : column + row];
      return {
        row,
        column,
        seenPercent: cell.seen_percent,
        seenPairs: cell.seen_pairs,
        possiblePairs: cell.possible_pairs,
        level: level(cell.seen_percent, peak),
      };
    }),
  );
  return { sections, rows };
}
