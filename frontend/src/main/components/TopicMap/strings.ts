// User-facing Spanish text of the topic map. Only strings used by application/topicSummary.ts so far.
export const PERIODS = {
  early: "2000–2009",
  middle: "2011–2023",
  recent: "2024–2025",
} as const;

export const noDocuments = "No hay documentos de este tema desde 2000.";

export const noPeriodData = "No hay documentos de este tema en los periodos 2000–2009, 2011–2023 ni 2024–2025.";

export const docsPerYear = (n: string, kind: "zero" | "less" | "one" | "many") =>
  kind === "less" ? "menos de 1 documento al año" : `${n} ${kind === "one" ? "documento" : "documentos"} al año`;

export const share = (n: string, kind: "less" | "almost" | "exact") =>
  kind === "less" ? "menos del 1 %" : kind === "almost" ? "casi el 100 %" : `el ${n} %`;
export const epShare = (sharePhrase: string) => `${sharePhrase} son traducciones de patentes europeas`;
export const periodAverage = (period: string, amount: string, ep: string | null) =>
  `en ${period}, ${amount} de media${ep ? ` (${ep})` : ""}`;

export const peakOne = (year: string) => `El año con más documentos fue ${year}`;
export const peakMany = (years: string) => `Los años con más documentos fueron ${years}`;
export const and = " y ";

export const noDominant = (years: string) => `Ningún solicitante domina en ${years}`;
export const noRecentDocuments = (years: string) => `No hay documentos de este tema en ${years}`;
export const dominantEvolution = (name: string, sharePhrase: string, years: string, without: string) =>
  `${name} figura como solicitante en ${sharePhrase} de los documentos de ${years}; sin los suyos, la media de esos años sería de ${without}`;
export const dominantSummary = (name: string, sharePhrase: string, years: string) =>
  `${name} figura como solicitante en ${sharePhrase} de los documentos de ${years}`;

export const total = (n: string, one: boolean) =>
  `Desde 2000 hay ${n} ${one ? "documento" : "documentos"} de este tema`;
export const averages = (recent: string, middle: string) =>
  `De media, ${recent} en ${PERIODS.recent} y ${middle} en ${PERIODS.middle}`;
export const averageOne = (amount: string, period: string) => `De media, ${amount} en ${period}`;

// ---- Views (Task 10) ----
export const home = "Inicio";
export const crumbSeparator = " › ";
export const breadcrumbLabel = "Dónde estás";
export const entryHeading = "¿Qué tecnología te interesa?";
export const searchLabel = "Buscar un tema";
export const noTopic = "No tenemos ese tema todavía.";
export const loading = "Cargando…";
export const unavailable = "Datos no disponibles";
export const unreviewedMark = "Nombres sin revisar";
export const help = "Cómo leer esto";
export const close = "Cerrar";
export const helpHeading = "Cómo leer esto";
export const helpPoints = [
  "Los datos son de las patentes publicadas en España entre 2000 y 2025 (corpus de la OEPM).",
  "Una parte grande son traducciones de patentes europeas.",
  "La fecha es la de publicación en España, no la de la invención ni la de la solicitud.",
  "2010 no tiene datos.",
  "Nada de lo que ves aquí dice qué es nuevo ni qué se puede patentar.",
] as const;

export const views = {
  evolucion: "¿Cómo evoluciona?",
  tema: "¿De qué trata?",
  quien: "¿Quién está?",
  pistas: "Pistas sin explorar",
} as const;

export const noData = "sin datos";
export const documentsIn = (year: number, n: string) => `${year}: ${n} ${n === "1" ? "documento" : "documentos"}`;
export const noDataIn = (year: number) => `${year}: sin datos`;
export const allDocuments = "Todos los documentos";
export const onlyApplicant = (name: string) => `Solo los de ${name}`;
export const axisReminder =
  "El eje es el año de publicación en España. Una traducción de patente europea publicada en 2025 se solicitó, de media, unos 7 años antes.";

export const documents = (n: string) => `${n} ${n === "1" ? "documento" : "documentos"}`;
export const more = (n: number) => `Ver ${n} más`;
export const neighboursHeading = "Temas que aparecen cerca";
export const subareasHeading = "Partes del tema";
export const applicantsHeading = "Solicitantes";
export const themesSentence = (name: string, pct: string) =>
  `Lo más habitual es ${name} (${pct} % de los documentos). Un mismo documento puede estar en más de una.`;
export const neighboursSentence = (names: string[]) =>
  `Aparecen sobre todo junto a ${names.length > 1 ? `${names.slice(0, -1).join(", ")}${and}${names[names.length - 1]}` : names[0]}.`;
export const playersSentence = (top: string, pct: string, others: string[]) =>
  `${top} figura como solicitante en el ${pct} % de los documentos.${others.length ? ` Después, ${others.join(and)}.` : ""}`;
export const applicantsNote = "Las variantes de un mismo nombre solo se unen para los solicitantes más conocidos.";
export const cluesIntro = (joined: string) =>
  `Aparecen ${joined} menos veces de las que sugiere su tamaño. Son pistas para investigar, no oportunidades: no se ha comprobado si hay algo nuevo ahí.`;
export const clueRow = (observed: string, once: boolean, joined: string, expected: string) =>
  `Aparece ${observed} ${once ? "vez" : "veces"} ${joined}; por su tamaño cabría esperar unas ${expected}.`;
export const noClues = "Ningún tema vecino cumple el criterio provisional todavía.";
export const provisional = "El criterio es provisional y no está validado.";
