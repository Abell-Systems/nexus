import type { SensitivityResults } from "../domain/whitespace";

export interface SensitivityRow {
  origin: string;
  observed: number;
  removedYearMin: number;
  removedYearMax: number;
  shortenedHistory: number;
  simulatedLow: number;
  simulatedHigh: number;
}

/** The positives under each scenario, as the results state them (the study's counts, not an opportunity count). */
export function sensitivityRows(results: SensitivityResults): SensitivityRow[] {
  return Object.entries(results.sensitivity).map(([origin, scenarios]) => {
    const removed = Object.values(scenarios["S-B1"]).map((figures) => figures.positives);
    return {
      origin,
      observed: scenarios["S-A"].positives,
      removedYearMin: Math.min(...removed),
      removedYearMax: Math.max(...removed),
      shortenedHistory: scenarios["S-B2"].positives,
      simulatedLow: scenarios["S-C"].positives["p2.5"],
      simulatedHigh: scenarios["S-C"].positives["p97.5"],
    };
  });
}
