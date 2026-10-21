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
  served: "bundled" | "on_demand";
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
    "Una ausencia observada indica que no se ha observado co-clasificación en este corpus y periodo. No demuestra que las áreas no se combinen ni que exista una oportunidad tecnológica.",
  status: "White spaces predictivos: no disponible. Pendiente de validación científica.",
  notValidation:
    "Esta página describe resultados ya medidos. No demuestra que ningún método predictivo funcione.",
  yUnknown:
    "Qué denota exactamente el tipo Y no se ha leído, y el inventario no incluye clasificaciones: el efecto de estas ausencias sobre los resultados no se puede estimar con los datos disponibles.",
} as const;

// docs/whitespace/oepm-subclass-pairs-results.json, as versioned. Unseen pairs are not stored: they are the complement of `pairs`.
export interface PairRecord {
  documents: number;
  by_year: Record<string, number>;
  first_year: number;
}

export interface OriginPairs {
  origin: number;
  min_documents: number;
  active: Record<string, number>;
  pairs: Record<string, PairRecord>;
}

export type PairsResults = Record<string, OriginPairs>;

// Fixed texts of docs/whitespace/product-vertical-2-contract.md section 3.
export const EXPLORER_TEXT = {
  unseen: "no observada en este corpus y periodo",
  noYear: "no observada",
  limits:
    "Límites del corpus: faltan todas las publicaciones de tipo Y de 2000 a 2009 y todo el año 2010, y hay huecos menores en 2011–2020. La historia empieza en 2000, así que el origen 2006 cuenta con 7 años. Un periodo sin publicaciones en el corpus no se lee como ausencia de actividad.",
  universe:
    "Solo se listan subclases activas en el origen (al menos 20 documentos publicados hasta él); las demás no aparecen.",
  symbolsOnly: "Solo se muestran símbolos IPC, sin títulos.",
  definitions:
    "Documentos con ambas: identificadores de publicación cuyos registros fuente llevan las dos subclases, hasta el origen. Primer año visto juntas: el primer año de publicación con una coincidencia. Coincidencias por año: el mismo recuento por año de publicación. Son tres medidas distintas.",
  noScore: "Sin puntuación ni ranking: el orden lo elige quien consulta y se etiqueta con el nombre de la columna.",
} as const;
