import { readFileSync } from "node:fs";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EntryBlock } from "../../src/main/components/WhiteSpace/EntryBlock";
import { WhiteSpacePage } from "../../src/main/components/WhiteSpace/WhiteSpacePage";
import { ENTRY_TEXT as T, TEXT, UNOBSERVED_TEXT } from "../../src/main/domain/whitespace";
import { UNOBSERVED_PAIRS_URL, resetUnobservedPairsCache } from "../../src/main/infrastructure/unobservedPairsLoader";

// These tests render the whole page over the real committed result (and its real hash): a longer limit for this file only.
vi.setConfig({ testTimeout: 30_000 });

const file = new Uint8Array(readFileSync("public/data/oepm-unobserved-pairs-results.json"));
const serve = () => vi.fn(async () => new Response(file));

beforeEach(() => {
  resetUnobservedPairsCache();
  window.location.hash = "";
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const entry = () => screen.getByRole("region", { name: T.title });
const pairs = () => document.getElementById("pares-no-observados")!;

describe("EntryBlock alone", () => {
  it("shouldStateWhatTheToolShowsWithTheNoticeTheStatusLineAndTheLinkToTheMeasurement", () => {
    render(<EntryBlock onSubmit={() => {}} />);
    expect(screen.getByRole("heading", { name: T.title })).toBeTruthy();
    expect(screen.getByText(T.sentence)).toBeTruthy();
    expect(screen.getByRole("link", { name: T.howMeasured }).getAttribute("href")).toBe("#cobertura");
    expect(entry().textContent).toContain(UNOBSERVED_TEXT.notice);
    expect(entry().textContent).toContain(TEXT.status);
    expect(screen.getByRole("link", { name: "ADR 0036" }).getAttribute("href")).toMatch(/0036-technology-white-space/);
  });

  it("shouldOfferNoExampleSymbolAndNoSuggestionWhenRendered", () => {
    render(<EntryBlock onSubmit={() => {}} />);
    expect(entry().textContent).not.toMatch(/ejemplos/i);
    expect(within(entry()).queryAllByRole("listitem")).toHaveLength(0);
    expect(within(entry()).getAllByRole("button").map((b) => b.textContent)).toEqual([T.submit]);
  });

  it("shouldHandTheTypedSymbolAndTheChosenSectionToTheCallerWhenSubmitted", () => {
    const onSubmit = vi.fn();
    render(<EntryBlock onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "G06N" } });
    fireEvent.change(screen.getByLabelText(T.section), { target: { value: "H" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith("G06N", "H");
  });

  it("shouldOfferTheEightIpcSectionsAndNone", () => {
    render(<EntryBlock onSubmit={() => {}} />);
    const options = within(screen.getByLabelText(T.section)).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual([T.noSection, "A", "B", "C", "D", "E", "F", "G", "H"]);
  });
});

describe("EntryBlock in the front page", () => {
  it("shouldFetchNothingWhenThePageOpensOrWhenSomethingIsTypedInTheBlock", () => {
    const fetcher = serve();
    vi.stubGlobal("fetch", fetcher);
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "A01B" } });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("shouldKeepTheSixPartsInTheContractualOrderAndPutTheBlockBetweenTheLeadAndTheBanner", () => {
    const { container } = render(<WhiteSpacePage />);
    const ids = [...container.querySelectorAll("main > section")].map((s) => s.id).filter(Boolean);
    const contractual = ["resumen", "cobertura", "mapa", "sensibilidad", "trazabilidad", "estado"];
    expect(ids.filter((id) => contractual.includes(id))).toEqual(contractual);
    const follows = (a: Node, b: Node) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    const h1 = screen.getByRole("heading", { level: 1 });
    const banner = screen.getByText(TEXT.notValidation).closest("p")!;
    expect(follows(h1, entry())).toBe(true);
    expect(follows(entry(), banner)).toBe(true);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("shouldTakeASymbolToTheUnobservedPairsSectionFetchOnceSelectItAndMoveTheFocusThereWhenSubmitted", async () => {
    const fetcher = serve();
    vi.stubGlobal("fetch", fetcher);
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "a01b" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    expect(window.location.hash).toBe("#pares-no-observados");
    await waitFor(() => expect(within(pairs()).getByRole("table")).toBeTruthy());
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher).toHaveBeenCalledWith(UNOBSERVED_PAIRS_URL, { cache: "no-store" });
    const rows = within(within(pairs()).getByRole("table")).getAllByRole("row").slice(1);
    for (const row of rows) expect(within(row).getAllByRole("rowheader")[0].textContent === "A01B" || within(row).getAllByRole("cell")[0].textContent === "A01B").toBe(true);
    expect(document.activeElement).toBe(within(pairs()).getByLabelText("Buscar subclase por símbolo"));
  });

  it("shouldTakeASectionAloneAndListItsPairsWhenSubmitted", async () => {
    vi.stubGlobal("fetch", serve());
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.section), { target: { value: "H" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    await waitFor(() => expect(within(pairs()).getByRole("table")).toBeTruthy());
    expect((within(pairs()).getByLabelText("Sección") as HTMLSelectElement).value).toBe("H");
  });

  it("shouldFetchOnceAndKeepTheFocusInTheSectionWhenNothingMatchesTheText", async () => {
    const fetcher = serve();
    vi.stubGlobal("fetch", fetcher);
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "ZZZZ" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(within(pairs()).getByLabelText("Sección").querySelectorAll("option").length).toBeGreaterThan(1));
    expect(within(pairs()).queryByRole("table")).toBeNull();
    expect(within(pairs()).queryAllByRole("button", { name: /^ZZZZ/ })).toHaveLength(0);
    expect(document.activeElement).toBe(within(pairs()).getByLabelText("Buscar subclase por símbolo"));
  });

  it("shouldShowTheLoadErrorFetchOnceAndKeepTheFocusInTheSectionWhenTheFileIsMissing", async () => {
    const fetcher = vi.fn(async () => new Response("", { status: 404 }));
    vi.stubGlobal("fetch", fetcher);
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "A01B" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    expect((await within(pairs()).findByRole("alert")).textContent).toContain(UNOBSERVED_TEXT.loadError);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(within(pairs()).queryByRole("table")).toBeNull();
    expect(document.activeElement).toBe(within(pairs()).getByLabelText("Buscar subclase por símbolo"));
  });

  it("shouldShowTheIntegrityErrorAndNoPairWhenAByteOfTheFileIsChanged", async () => {
    const tampered = file.slice();
    tampered[tampered.indexOf(0x41)] = 0x42;
    vi.stubGlobal("fetch", vi.fn(async () => new Response(tampered)));
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "A01B" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    expect((await within(pairs()).findByRole("alert")).textContent).toBe(UNOBSERVED_TEXT.integrityError);
    expect(within(pairs()).queryByRole("table")).toBeNull();
  });

  it("shouldNotSelectASymbolTypedWithOnlyPartOfItWhenTheTextIsAPrefixOfAnActiveOne", async () => {
    vi.stubGlobal("fetch", serve());
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "A01" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    await waitFor(() => expect(within(pairs()).getAllByRole("button", { name: /^A01/ }).length).toBeGreaterThan(1));
    expect(within(pairs()).queryByRole("table")).toBeNull();
  });

  it("shouldOnlyShowMatchesAndNoTableWhenTheTextIsNotExactlyAnActiveSymbol", async () => {
    vi.stubGlobal("fetch", serve());
    render(<WhiteSpacePage />);
    fireEvent.change(screen.getByLabelText(T.subclass), { target: { value: "G06" } });
    fireEvent.click(screen.getByRole("button", { name: T.submit }));
    await waitFor(() => expect(within(pairs()).getAllByRole("button", { name: /^G06/ }).length).toBeGreaterThan(0));
    expect(within(pairs()).queryByRole("table")).toBeNull();
  });
});

// Contract of vertical 3, section 4: whole terms, without case or accents, singular and plural; only the allowlisted sentences may contain a listed word.
describe("forbidden formulations in the entry block", () => {
  const WORDS = ["oportunidad", "hueco prometedor", "potencial", "atractivo", "recomendado", "mejor", "top", "ranking", "puntuacion", "probabilidad", "p-valor", "significativo", "white space", "innovacion", "euro", "dolar", "precio", "mercado", "ventas", "ingresos", "rentabilidad", "inversion", "negocio", "comercial"];
  const plain = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

  it("shouldFindNoListedWordOutsideTheAllowlistedStatusLine", () => {
    render(<EntryBlock onSubmit={() => {}} />);
    const text = plain((entry().textContent ?? "").split(TEXT.status).join(" "));
    expect(text).not.toMatch(/[€$]/);
    for (const w of WORDS) expect(text, w).not.toMatch(new RegExp(`(?<![\\p{L}\\p{N}])${w}(?:s|es)?(?![\\p{L}\\p{N}])`, "u"));
    const names = [...entry().querySelectorAll("label,button,a,option,legend")].map((e) => plain(e.textContent ?? "")).join(" ");
    for (const w of WORDS) expect(names, w).not.toMatch(new RegExp(`(?<![\\p{L}\\p{N}])${w}(?:s|es)?(?![\\p{L}\\p{N}])`, "u"));
  });
});
