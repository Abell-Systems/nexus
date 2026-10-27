import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { reconstructExpected } from "../../src/main/application/expectedTerms";
import { PairEvidenceSheet } from "../../src/main/components/WhiteSpace/PairEvidenceSheet";
import { SHEET_TEXT as T, TEXT, UNOBSERVED_TEXT, type UnobservedPairsResults } from "../../src/main/domain/whitespace";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const data = JSON.parse(readFileSync(join(root, "docs", "whitespace", "oepm-unobserved-pairs-results.json"), "utf8")) as UnobservedPairsResults;
const A = "A01B";
const B = "A01J";
const authority = { name: "ES_Authority_File_20260930.zip", sha256: "80a7fe1713f7b63f150f3601239dea06e0c7ddb274fa9242daa904c5a93731f1" };
const SHA = "6a269125d4d92725d74a875f1264553bacb798dac0b1ef7061508027fb3482f7";

afterEach(cleanup);

const open = (d: UnobservedPairsResults = data, onClose = () => {}) =>
  render(<PairEvidenceSheet data={d} a={A} b={B} resultSha256={SHA} authorityFile={authority} onClose={onClose} />);

describe("PairEvidenceSheet", () => {
  it("shouldShowTheSymbolsTheDocumentsTheZeroBothTextAndTheAbsenceSentenceWhenOpened", () => {
    const { container } = open();
    expect(screen.getByRole("region", { name: `${T.title} ${A} y ${B}` })).toBeTruthy();
    expect(container.textContent).toContain(`${A}: ${new Intl.NumberFormat("es-ES").format(data.active[A])} documentos`);
    expect(container.textContent).toContain(T.bothZero);
    expect(screen.getByText(TEXT.absenceIsNotOpportunity)).toBeTruthy();
    for (const title of [T.documents, T.termsTitle, T.identityTitle]) expect(screen.getByRole("heading", { name: title })).toBeTruthy();
  });

  it("shouldShowTheSumNextToTheStoredValueAndFoldTheTermsTableWhenConcordant", () => {
    open();
    const expected = reconstructExpected(data.documents_by_year[A], data.documents_by_year[B], data.documents_per_year, data.pairs[A][B]);
    const table = screen.getByRole("table", { name: T.termsTitle });
    const folded = table.closest("details")!;
    expect(folded.hasAttribute("open")).toBe(false);
    expect(within(folded).getByText("Tabla de los términos por año", { selector: "summary" })).toBeTruthy();
    expect(within(table).getAllByRole("row").length).toBe(1 + expected.terms.length);
    // the sum and the stored value stay visible outside the folded table, with the nine stored decimals
    expect(screen.getAllByText("0,554177296", { selector: "dd" })).toHaveLength(2);
    expect(screen.getByRole("status").textContent).toBe(T.concordant);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shouldShowTheTermsWithFourDecimalsByDefaultAndWithNineWhenFullPrecisionIsAsked", () => {
    open();
    const table = screen.getByRole("table", { name: T.termsTitle });
    const firstTerm = () => within(within(table).getAllByRole("row")[1]).getAllByRole("cell").at(-1)!.textContent;
    expect(firstTerm()).toBe("0,0255");
    const toggle = screen.getByRole("button", { name: "Mostrar precisión completa" });
    expect(toggle.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-pressed")).toBe("true");
    expect(firstTerm()).toBe("0,025518175");
    // presentation only: the sum, the stored value and the verdict do not change with the precision of the terms
    expect(screen.getAllByText("0,554177296", { selector: "dd" })).toHaveLength(2);
    expect(screen.getByRole("status").textContent).toBe(T.concordant);
  });

  it("shouldShowTheDiscrepancyAndKeepTheStoredValueWhenTheStoredValueDiffersByOneUnitOfTheLastDecimal", () => {
    const altered = structuredClone(data);
    altered.pairs[A][B] = Math.round((altered.pairs[A][B] + 1e-9) * 1e9) / 1e9;
    open(altered);
    expect(screen.getByRole("alert").textContent).toContain(T.discrepancy);
    expect(screen.queryByText(T.concordant)).toBeNull();
    expect(screen.getByText("0,554177297", { selector: "dd" })).toBeTruthy(); // the stored value is shown as it is, not corrected
    expect(screen.getByText("0,554177296", { selector: "dd" })).toBeTruthy(); // and the reconstructed sum beside it
  });

  it("shouldMarkTheYearWithoutPublicationsAsAGapAndNeverAsAZero", () => {
    const { container } = open();
    expect("2010" in data.documents_per_year).toBe(false);
    const gaps = container.querySelectorAll("rect[data-gap='2010']");
    expect(gaps).toHaveLength(2); // one per chart
    for (const gap of gaps) expect(gap.querySelector("title")?.textContent).toBe(`2010: ${T.gap}`);
    const table = screen.getByRole("table", { name: T.activityTitle });
    const row = within(table).getByRole("rowheader", { name: "2010" }).closest("tr")!;
    expect(within(row).getByText(T.gap)).toBeTruthy();
    expect(within(row).queryByText("0")).toBeNull();
  });

  it("shouldDrawBothChartsOnTheSameScaleWhoseMaximumIsTheLargestCountOfEither", () => {
    const { container } = open();
    const charts = container.querySelectorAll("svg[data-max]");
    expect(charts).toHaveLength(2);
    const maxima = [...charts].map((c) => Number(c.getAttribute("data-max")));
    const largest = Math.max(...Object.values(data.documents_by_year[A]), ...Object.values(data.documents_by_year[B]));
    expect(maxima).toEqual([largest, largest]);
    for (const chart of charts) expect(chart.getAttribute("role")).toBe("img");
  });

  it("shouldReadTheActivityBeforeTheZeroBothTextAndTheAbsenceSentence", () => {
    const { container } = open();
    const charts = container.querySelectorAll("svg[data-max]");
    const lastChart = charts[charts.length - 1];
    const zero = screen.getByText(`${T.bothZero}.`);
    const absence = screen.getByText(TEXT.absenceIsNotOpportunity);
    const follows = (x: Node, y: Node) => Boolean(x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(follows(lastChart, zero)).toBe(true);
    expect(follows(zero, absence)).toBe(true);
    expect(follows(absence, screen.getByRole("heading", { name: T.termsTitle }))).toBe(true);
  });

  it("shouldIdentifyEachSubclassWithALegendAndACaptionOverItsChart", () => {
    const { container } = open();
    const legend = container.querySelector("p[class*='legend']")!;
    expect(legend.textContent).toBe(`${A}${B}`);
    const captions = [...container.querySelectorAll("p[class*='note']")].map((p) => p.textContent);
    expect(captions).toContain(A);
    expect(captions).toContain(B);
  });

  it("shouldFoldTheCorpusHashesByDefaultWithoutHidingTheConfigurationOrTheResultHash", () => {
    open();
    const files = screen.getByRole("table", { name: "Ficheros del corpus" }).closest("details")!;
    expect(files.hasAttribute("open")).toBe(false);
    expect(files.contains(screen.getByText(SHA))).toBe(false);
    expect(files.contains(screen.getByText(data.configuration.id))).toBe(false);
  });

  it("shouldOfferTheActivityDataAsATableForKeyboardAndScreenReaderUsers", () => {
    open();
    const table = screen.getByRole("table", { name: T.activityTitle });
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Año", UNOBSERVED_TEXT.columns.docsA, UNOBSERVED_TEXT.columns.docsB]);
  });

  it("shouldReserveTheBlockOfTheListsWithoutSimulatingAnyList", () => {
    const { container } = open();
    const heading = screen.getByRole("heading", { name: T.listsTitle });
    expect(heading.nextElementSibling?.textContent).toBe(T.listsUnavailable);
    expect(container.querySelector("ul, ol")).toBeNull();
  });

  it("shouldShowTheTraceabilityWithTheVerifiedResultHashTheConfigurationAndTheInventoryOfTheExposureResult", () => {
    const { container } = open();
    expect(screen.getByText(SHA)).toBeTruthy();
    expect(screen.getByText(data.configuration.id)).toBeTruthy();
    expect(screen.getByText(authority.sha256)).toBeTruthy();
    expect(container.textContent).toContain("tomado del resultado de exposición");
    const files = within(screen.getByRole("table", { name: "Ficheros del corpus" })).getAllByRole("row").length - 1;
    expect(files).toBe(Object.keys(data.corpus.files).length);
    expect(container.textContent).toContain(TEXT.attribution);
  });

  it("shouldShowTheLimitsTheFixedParametersAndTheQuestionsBeforeInterpretingWithoutAnyRecommendation", () => {
    open();
    for (const text of [UNOBSERVED_TEXT.limits, UNOBSERVED_TEXT.parameters, T.beforeInterpreting]) expect(screen.getByText(text)).toBeTruthy();
  });

  it("shouldCallOnCloseWhenTheCloseButtonIsPressed", () => {
    const onClose = vi.fn();
    open(data, onClose);
    fireEvent.click(screen.getByRole("button", { name: T.close }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shouldRenderNothingWhenThePairIsNotInTheResult", () => {
    const { container } = render(<PairEvidenceSheet data={data} a="A01B" b="Z99Z" resultSha256={SHA} authorityFile={authority} onClose={() => {}} />);
    expect(container.textContent).toBe("");
  });
});

// Contract section 4: whole terms, no case or accents, singular and plural; only the allowlisted sentences may contain a listed word.
describe("forbidden formulations on the sheet", () => {
  const WORDS = ["oportunidad", "hueco prometedor", "potencial", "atractivo", "recomendado", "mejor", "top", "ranking", "puntuacion", "probabilidad", "p-valor", "significativo", "white space", "innovacion", "euro", "dolar", "precio", "mercado", "ventas", "ingresos", "rentabilidad", "inversion", "negocio", "comercial"];
  const plain = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

  it.each([[data], [Object.assign(structuredClone(data), { pairs: { [A]: { [B]: data.pairs[A][B] + 1e-9 } } })]])(
    "shouldFindNoListedWordInTheSheetInEitherOfItsStates",
    (d) => {
      const { container } = open(d as UnobservedPairsResults);
      let text = container.textContent ?? "";
      text = text.split(TEXT.absenceIsNotOpportunity).join(" ");
      const clean = plain(text);
      expect(clean).not.toMatch(/[€$]/);
      for (const w of WORDS) expect(clean, w).not.toMatch(new RegExp(`(?<![\\p{L}\\p{N}])${w}(?:s|es)?(?![\\p{L}\\p{N}])`, "u"));
      const names = [...container.querySelectorAll("[aria-label],title,desc,summary,th,dt,button")]
        .map((e) => plain(e.getAttribute("aria-label") ?? e.textContent ?? ""))
        .join(" ");
      for (const w of WORDS) expect(names, w).not.toMatch(new RegExp(`(?<![\\p{L}\\p{N}])${w}(?:s|es)?(?![\\p{L}\\p{N}])`, "u"));
    },
  );
});
