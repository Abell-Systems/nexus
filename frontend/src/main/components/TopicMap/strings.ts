// User-facing Spanish text of the topic map. Only strings used by application/topicSummary.ts so far.
export const PERIODS = {
  early: "2000–2009",
  middle: "2011–2023",
  recent: "2024–2025",
} as const;

export const noDocuments = "No hay documentos de este tema desde 2000.";

export const perYear = (avg: string) => `${avg} al año`;
export const epShare = (pct: string) => `${pct} % traducciones de patentes europeas`;
export const periodAverage = (period: string, avg: string, ep: string | null) =>
  `en ${period}, ${perYear(avg)} de media${ep ? ` (${ep})` : ""}`;

export const peakOne = (year: string) => `El año con más documentos fue ${year}`;
export const peakMany = (years: string) => `Los años con más documentos fueron ${years}`;
export const and = " y ";

export const noDominant = (years: string) => `Ningún solicitante domina en ${years}`;
export const dominantEvolution = (name: string, pct: string, years: string, without: string) =>
  `${name} firma el ${pct} % de los documentos de ${years}; sin los suyos, la media de esos años sería de ${perYear(without)}`;
export const dominantSummary = (name: string, pct: string, years: string) =>
  `${name} firma el ${pct} % de los documentos de ${years}`;

export const total = (n: string) => `Desde 2000 hay ${n} documentos de este tema`;
export const averages = (recent: string, middle: string) =>
  `De media, ${recent} en ${PERIODS.recent} y ${middle} en ${PERIODS.middle}`;
export const averageOne = (avg: string, period: string) => `De media, ${avg} en ${period}`;
