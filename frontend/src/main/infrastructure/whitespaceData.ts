import corpusIdentity from "./data/oepm_biblio_2000_2025.json";
import exposure from "./data/oepm-corpus-exposure-results.json";
import sensitivity from "./data/oepm-omission-sensitivity-results.json";
import density from "./data/oepm-section-density-results.json";
import provenance from "./data/provenance.json";
import type {
  CorpusIdentity,
  DensityResults,
  ExposureResults,
  Provenance,
  SensitivityResults,
} from "../domain/whitespace";

// Static copies of the versioned results (`npm run sync-data`); a test requires them to be identical to the originals.
export const whitespaceData = {
  exposure: exposure as unknown as ExposureResults,
  density: density as unknown as DensityResults,
  sensitivity: sensitivity as unknown as SensitivityResults,
  corpusIdentity: corpusIdentity as unknown as CorpusIdentity,
  provenance: provenance as Provenance,
};
