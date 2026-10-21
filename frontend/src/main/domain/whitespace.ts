// The results of the white-space study, exactly as the repository versions them. Nothing here is derived.

export type KindGroup = "ep_translation" | "kind_y" | "other";

export interface YearGroup {
  inventory: number;
  present: number;
  absent: number;
  absent_share_percent: number;
}

export type ExposureYear = Record<KindGroup, YearGroup> & { corpus_keys_not_in_inventory: number };

export interface Accumulated {
  calendar_years_in_window: number;
  years_with_corpus_publications: number;
  all_groups: { inventory: number; absent: number; absent_share_percent: number };
  kind_y: { inventory: number; absent: number; absent_share_percent: number };
}

export interface ExposureResults {
  authority_file: { name: string; sha256: string };
  exposure: {
    inventory_publications: number;
    corpus_publications: number;
    by_year: Record<string, ExposureYear>;
    accumulated_up_to_origin: Record<string, Accumulated>;
  };
}

export interface DensityCell {
  possible_pairs: number;
  seen_pairs: number;
  seen_percent: number;
}

export interface SectionDensity {
  origin: number;
  min_documents: number;
  active_subclasses: number;
  active_subclasses_by_section: Record<string, number>;
  seen_pairs: number;
  cells: Record<string, DensityCell>;
}

export type DensityResults = Record<string, SectionDensity>;

export interface SensitivityQuantities {
  active_subclasses: number;
  candidate_pairs: number;
  positives: number;
  positive_rate_percent: number;
}

export interface SensitivityOrigin {
  "S-A": SensitivityQuantities;
  "S-B1": Record<string, SensitivityQuantities>;
  "S-B2": SensitivityQuantities;
  "S-C": { replications: number; positives: { mean: number; "p2.5": number; "p97.5": number } };
}

export interface SensitivityResults {
  sensitivity: Record<string, SensitivityOrigin>;
}

export interface CorpusIdentity {
  files: Record<string, { sha256: string; bytes: number }>;
}

export interface ProvenanceFile {
  file: string;
  source: string;
  producedBy: string;
  pullRequest: number;
  bytes: number;
  sha256: string;
}

export interface Provenance {
  files: ProvenanceFile[];
}

// Fixed texts that carry the rules of docs/whitespace/product-vertical-1-contract.md section 2.
export const TEXT = {
  attribution: "Origen de los datos: Oficina Española de Patentes y Marcas",
  noSponsorship: "La Oficina Española de Patentes y Marcas no participa en este producto ni lo patrocina ni lo apoya.",
  absenceIsNotOpportunity:
    "Una ausencia observada no es una oportunidad tecnológica: la mayoría refleja que dos áreas no suelen combinarse.",
  status: "White spaces predictivos: no disponible. Pendiente de validación científica.",
  notValidation:
    "Esta página describe resultados ya medidos. No demuestra que ningún método predictivo funcione.",
  yUnknown:
    "Qué denota exactamente el tipo Y no se ha leído, y el inventario no incluye clasificaciones: el efecto de estas ausencias sobre los resultados no se puede estimar con los datos disponibles.",
} as const;
