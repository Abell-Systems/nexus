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
