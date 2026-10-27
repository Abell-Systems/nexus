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
  // Date recorded in docs/whitespace/oepm-biblio-corpus-characterization.md (section 1) and shown by the mtime of the 26 files.
  // It is the download date; the OEPM's own update date of the data has not been checked.
  downloadDate:
    "Ficheros bibliográficos 2000–2025 descargados de la OEPM el 20 de octubre de 2026 (fecha de descarga, no la fecha de actualización que la OEPM atribuya a los datos).",
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
  first_years: Record<string, number>;
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

// docs/whitespace/oepm-unobserved-pairs-results.json (ADR 0038 E3). Only unobserved pairs are stored: pairs[a][b] with a < b is the expected count.
export interface UnobservedPairsResults {
  origin: number;
  min_documents: number;
  e_min: number;
  active: Record<string, number>;
  pairs: Record<string, Record<string, number>>;
}

// Texts of docs/whitespace/vertical-3-texts-proposal.md as approved by the owner (T05, T06 and T03 are the allowlisted sentences of the contract section 4).
export const UNOBSERVED_TEXT = {
  title: "Pares no observados (exploratorio)",
  notice: "Exploratorio. Sin validar. Ningún orden mostrado aquí es una predicción. El estudio no ha demostrado que ningún orden prediga nada (ADR 0036).",
  expectedSortNotice:
    "Orden por esperado bajo independencia: refleja cuántas coincidencias se esperarían si las dos subclases fueran independientes; no mide probabilidad de aparición ni interés.",
  parameters:
    "Parámetros fijados por diseño, no ajustados a los resultados: una subclase es activa con al menos 20 identificadores de publicación; el esperado mínimo para el tipo con esperado ≥ 1 es 1.",
  limits:
    "Límites del corpus: faltan las publicaciones de tipo Y de 2000 a 2009 y todo el año 2010; hay huecos menores en 2011–2020. Las traducciones de patentes europeas caen en 2023. Un periodo sin publicaciones en el corpus no se lee como ausencia de actividad. La completitud de 2025 se ha comparado con el inventario de la OEPM (como máximo un 1 % de ausencias por grupo); no es una prueba de integridad absoluta del corpus.",
  columns: { a: "Subclase A", b: "Subclase B", expected: "Esperado bajo independencia (coincidencias)", docsA: "Documentos de A", docsB: "Documentos de B" },
  sorts: { symbol: "por símbolo (predeterminado)", docsA: "por documentos de A", docsB: "por documentos de B", expected: "por esperado bajo independencia" },
  types: { all: "Tipo: todos los pares no observados", expected: "Tipo: no observados con esperado ≥ 1 bajo independencia" },
  none: "No hay pares que cumplan los filtros seleccionados. Esto no demuestra que no exista actividad tecnológica.",
  noPairsForSubclass: "Esta subclase no tiene pares no observados con las demás subclases activas del corpus hasta 2025.",
  start: "Elige una subclase o una sección para empezar. No se muestra ningún par hasta entonces.",
  loading: "Cargando los datos…",
  loadError: "No se pudieron cargar los datos. No se muestra ningún resultado. Puede reintentar.",
  integrityError: "Los datos cargados no superan la comprobación de integridad. No se muestra ningún resultado.",
} as const;

// Entry block of the front page (docs/whitespace/frontend-entry-ux-proposal.md, option A). H1, H2 and H3 approved by the owner on 2026-10-27.
// H4 (the label of example symbols) and H5 (skip link) are not part of this block: the example symbols are not approved and the skip link
// belongs to the second pull request. The entries marked "label" are neutral names of fields that no list has approved yet.
export const ENTRY_TEXT = {
  title: "Pares de subclases IPC no observados en patentes españolas", // H1
  sentence: "Elija una subclase o una sección y vea qué combinaciones no aparecen juntas en el corpus de la OEPM hasta 2025.", // H2
  howMeasured: "Cómo se ha medido", // H3
  subclass: "Subclase IPC", // label
  section: "Sección IPC", // label
  noSection: "Ninguna", // label
  submit: "Buscar", // label
} as const;
