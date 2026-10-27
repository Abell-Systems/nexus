import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { UnobservedPairsSection } from "../../src/main/components/WhiteSpace/UnobservedPairsSection";
import { TEXT, UNOBSERVED_TEXT as T } from "../../src/main/domain/whitespace";
import { whitespaceData } from "../../src/main/infrastructure/whitespaceData";
import { UNOBSERVED_PAIRS_URL, resetUnobservedPairsCache } from "../../src/main/infrastructure/unobservedPairsLoader";

// These tests load the real 3 MB result and list or sort up to 149,048 pairs, with coverage instrumentation on the CI runner: the default
// 5 s was exceeded there (5.3 s) while it passes locally in about one second. A longer limit for this file only; nothing else changes.
vi.setConfig({ testTimeout: 30_000 });

// The real versioned file, so the manifest hash of provenance.json is exercised end to end.
const file = new Uint8Array(readFileSync("public/data/oepm-unobserved-pairs-results.json"));
const real = JSON.parse(new TextDecoder().decode(file)) as { active: Record<string, number>; pairs: Record<string, Record<string, number>> };

const serve = (bytes: Uint8Array, status = 200) => vi.fn(async () => new Response(bytes, { status }));
const touch = () => fireEvent.focus(screen.getByLabelText("Buscar subclase por símbolo"));
const pick = async (symbol: string) => {
  const search = screen.getByLabelText("Buscar subclase por símbolo");
  fireEvent.change(search, { target: { value: symbol } });
  fireEvent.click(await screen.findByRole("button", { name: new RegExp(`^${symbol} `) }));
};
const bodyRows = () => within(screen.getByRole("table")).getAllByRole("row").slice(1);

beforeEach(() => resetUnobservedPairsCache());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("UnobservedPairsSection", () => {
  it("shouldFetchNothingAndListNothingWhenOpened", () => {
    const fetcher = serve(file);
    vi.stubGlobal("fetch", fetcher);
    render(<UnobservedPairsSection />);
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByText(T.start)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("shouldListNoPairBeforeASubclassOrSectionIsChosenEvenWhenDataLoaded", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await screen.findByRole("option", { name: "H" });
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByText(T.start)).toBeTruthy();
  });

  it("shouldListTheChosenSubclassPairsAlphabeticallyByDefaultWithOneDecimalWhenChosen", async () => {
    const fetcher = serve(file);
    vi.stubGlobal("fetch", fetcher);
    render(<UnobservedPairsSection />);
    touch();
    await pick("G06N");
    expect(fetcher).toHaveBeenCalledWith(UNOBSERVED_PAIRS_URL, { cache: "no-store" });
    const pairs = bodyRows().map((r) => [within(r).getByRole("rowheader").textContent!, within(r).getAllByRole("cell")[0].textContent!]);
    const all = Object.entries(real.pairs).flatMap(([x, m]) => Object.keys(m).filter((y) => x === "G06N" || y === "G06N").map((y) => [x, y]));
    const expected = all.sort(([a1, b1], [a2, b2]) => (a1 < a2 ? -1 : a1 > a2 ? 1 : b1 < b2 ? -1 : 1)).slice(0, 200);
    expect(pairs).toEqual(expected);
    const [a, b] = pairs[0];
    expect(a < b).toBe(true);
    expect(screen.queryByText(T.expectedSortNotice)).toBeNull();
  });

  it("shouldShowTheNoticeAndSortByExpectedDescendingOnlyWhenTheUserChoosesIt", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await pick("G06N");
    fireEvent.change(screen.getByLabelText("Orden"), { target: { value: "expected" } });
    expect(screen.getByText(T.expectedSortNotice)).toBeTruthy();
    const values = bodyRows().map((r) => Number(within(r).getAllByRole("cell")[3].textContent!.replace(",", ".")));
    expect(values).toEqual([...values].sort((x, y) => y - x));
    expect(screen.getByRole("columnheader", { name: T.columns.expected })).toBeTruthy();
  });

  it("shouldKeepOnlyPairsWithExpectedAtLeastOneWhenTypeIsExpected", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await pick("G06N");
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "expected" } });
    const values = bodyRows().map((r) => Number(within(r).getAllByRole("cell")[3].textContent!.replace(",", ".")));
    expect(values.length).toBeGreaterThan(0);
    expect(Math.min(...values)).toBeGreaterThanOrEqual(1);
  });

  it("shouldListPairsOfTheSectionWhenOnlyASectionIsChosen", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await screen.findByRole("option", { name: "H" });
    fireEvent.change(screen.getByLabelText("Sección"), { target: { value: "H" } });
    expect(bodyRows().length).toBe(200);
    expect(screen.getByRole("button", { name: "Mostrar más" })).toBeTruthy();
  });

  it("shouldShowTheLegitimateEmptyTextWhenFiltersMatchNothing", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await pick("A01L");
    fireEvent.change(screen.getByLabelText("Sección"), { target: { value: "D" } });
    expect(bodyRows().length).toBe(35);
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "expected" } });
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByText(T.none)).toBeTruthy();
  });

  it("shouldShowTheIntegrityErrorAndNoDataWhenAByteIsChanged", async () => {
    const tampered = file.slice();
    tampered[tampered.indexOf(0x41)] = 0x42; // changes one byte, the file may still be valid JSON
    vi.stubGlobal("fetch", serve(tampered));
    const parse = vi.spyOn(JSON, "parse");
    render(<UnobservedPairsSection />);
    touch();
    expect((await screen.findByRole("alert")).textContent).toBe(T.integrityError);
    expect(parse).not.toHaveBeenCalled();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByText(T.start)).toBeNull();
    parse.mockRestore();
  });

  it("shouldShowTheLoadErrorWithRetryWhenTheFileIsMissingAndRecoverWhenItReturns", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response("", { status: 404 })).mockImplementation(async () => new Response(file));
    vi.stubGlobal("fetch", fetcher);
    render(<UnobservedPairsSection />);
    touch();
    expect((await screen.findByRole("alert")).textContent).toContain(T.loadError);
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    await screen.findByRole("option", { name: "H" });
  });

  it("shouldShowTheMandatoryTextsBesideTheList", () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    for (const text of [T.title, T.parameters, T.limits, TEXT.absenceIsNotOpportunity]) expect(screen.getByText(text)).toBeTruthy();
    expect(screen.getByText(/Exploratorio\. Sin validar\./).textContent).toBe(`${T.notice} ADR 0036`);
    expect(screen.getByRole("link", { name: "ADR 0036" }).getAttribute("href")).toMatch(/0036-technology-white-space/);
  });
});

// Contract section 4: whole terms, no case or accents, singular and plural; € and $ as characters; only the three allowlisted sentences may contain a listed word.
describe("forbidden formulations", () => {
  const WORDS = ["oportunidad", "hueco prometedor", "potencial", "atractivo", "recomendado", "mejor", "top", "ranking", "puntuacion", "probabilidad", "p-valor", "significativo", "white space", "innovacion", "euro", "dolar", "precio", "mercado", "ventas", "ingresos", "rentabilidad", "inversion", "negocio", "comercial"];
  const plain = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
  const ALLOWED = [T.expectedSortNotice, TEXT.absenceIsNotOpportunity, TEXT.status];

  it("shouldFindNoListedWordInAnyStateOfTheSection", async () => {
    vi.stubGlobal("fetch", serve(file));
    const { container } = render(<UnobservedPairsSection />);
    touch();
    await pick("G06N");
    fireEvent.change(screen.getByLabelText("Orden"), { target: { value: "expected" } });
    let text = container.textContent ?? "";
    for (const sentence of ALLOWED) text = text.split(sentence).join(" ");
    const clean = plain(text);
    expect(clean).not.toMatch(/[€$]/);
    for (const w of WORDS) expect(clean, w).not.toMatch(new RegExp(`(?<![\\p{L}\\p{N}])${w}(?:s|es)?(?![\\p{L}\\p{N}])`, "u"));
    const labels = [...container.querySelectorAll("[aria-label],option,button,th,label")].map((e) => plain(`${e.getAttribute("aria-label") ?? ""} ${e.textContent ?? ""}`)).join(" ");
    for (const w of WORDS) expect(labels, w).not.toMatch(new RegExp(`(?<![\\p{L}\\p{N}])${w}(?:s|es)?(?![\\p{L}\\p{N}])`, "u"));
  });

  it("shouldHaveNoRankColumnOrPositionBadge", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await pick("G06N");
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual([T.columns.a, T.columns.b, T.columns.docsA, T.columns.docsB, T.columns.expected, "Ficha del par"]);
  });
});

describe("evidence sheet opened from the list", () => {
  it("shouldOpenTheSheetOfARowKeepTheListAndReturnFocusToTheRowWhenClosed", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await pick("G06N");
    const list = screen.getByRole("table");
    const rowsOf = () => within(list).getAllByRole("row").slice(1);
    const rowsBefore = rowsOf().length;
    const first = within(rowsOf()[0]).getByRole("button", { name: /Ver la evidencia del par/ });
    fireEvent.click(first);
    const sheet = screen.getByRole("region", { name: /^Evidencia del par / });
    expect(document.activeElement).toBe(sheet);
    expect(rowsOf().length).toBe(rowsBefore);
    fireEvent.click(within(sheet).getByRole("button", { name: "Cerrar la ficha" }));
    expect(screen.queryByRole("region", { name: /^Evidencia del par / })).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(first));
  });

  it("shouldShowTheSha256TheBundleVerifiedAndNotAnyOtherWhenTheSheetIsOpen", async () => {
    vi.stubGlobal("fetch", serve(file));
    render(<UnobservedPairsSection />);
    touch();
    await pick("G06N");
    fireEvent.click(within(bodyRows()[0]).getByRole("button", { name: /Ver la evidencia del par/ }));
    const sheet = screen.getByRole("region", { name: /^Evidencia del par / });
    const entry = whitespaceData.provenance.files.find((f) => f.file === "oepm-unobserved-pairs-results.json");
    expect(entry?.sha256).toBe(createHash("sha256").update(file).digest("hex"));
    expect(within(sheet).getByText(entry!.sha256)).toBeTruthy();
  });
});
