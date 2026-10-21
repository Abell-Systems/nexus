import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SubclassExplorerSection } from "../../src/main/components/WhiteSpace/SubclassExplorerSection";
import { EXPLORER_TEXT, TEXT, type PairsResults } from "../../src/main/domain/whitespace";
import { resetSubclassPairsCache } from "../../src/main/infrastructure/subclassPairsLoader";

const fixture: PairsResults = {
  "2006": { origin: 2006, min_documents: 20, active: { A01B: 250, G06N: 90 }, pairs: {} },
  "2022": {
    origin: 2022,
    min_documents: 20,
    active: { A01B: 250, A01C: 196, G06N: 90, G06F: 500, H04L: 40 },
    pairs: {
      "A01B|A01C": { documents: 16, by_year: { "2000": 3, "2003": 13 }, first_year: 2000 },
      "G06F|G06N": { documents: 30, by_year: { "2001": 10, "2004": 20 }, first_year: 2001 },
    },
  },
};
const FORBIDDEN = [/prometedor/i, /oportunidad (tecnol|de innov)\w* (detectad|identificad|encontrad)/i, /\bhueco\b/i, /candidat/i, /puntuaci[oó]n:/i, /probabilidad/i];

beforeEach(() => {
  resetSubclassPairsCache();
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => fixture })));
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// testing-library's fireEvent stands in for a user: no new dependency for the tests.
const user = {
  selectOptions: async (el: HTMLElement, value: string) => void fireEvent.change(el, { target: { value } }),
  click: async (el: HTMLElement) => void fireEvent.click(el),
};

async function open(symbol = "G06N") {
  render(<SubclassExplorerSection />);
  const search = await screen.findByLabelText("Buscar subclase por símbolo");
  await screen.findByRole("option", { name: "2006" });
  fireEvent.change(search, { target: { value: symbol } });
  fireEvent.keyDown(search, { key: "Enter" });
  return { user };
}

const symbols = () => within(screen.getByRole("table")).getAllByRole("rowheader").map((c) => c.textContent);

describe("the subclass explorer", () => {
  it("shouldLoadTheStaticFileOnDemandAndStateTheLimitsBesideTheOriginSelectorWhenRendered", async () => {
    render(<SubclassExplorerSection />);
    await screen.findByLabelText("Origen");
    expect(fetch).toHaveBeenCalledWith("/data/oepm-subclass-pairs-results.json");
    expect(document.body.textContent).toContain(EXPLORER_TEXT.limits);
    expect(screen.getByLabelText<HTMLSelectElement>("Origen").value).toBe("2022");
  });

  it("shouldListEveryOtherActiveSubclassWithItsPairStateWhenASubclassIsChosenByKeyboard", async () => {
    await open();
    expect(symbols()).toEqual(["A01B", "A01C", "G06F", "H04L"]);
    const row = screen.getByRole("row", { name: /G06F/ });
    expect(row.textContent).toContain("observada");
    expect(row.textContent).toContain("2001");
  });

  it("shouldShowNoObservadaNeverZeroOrAYearAndTheAbsenceSentenceWhenAPairIsUnseen", async () => {
    await open();
    const row = screen.getByRole("row", { name: /H04L/ });
    expect(row.textContent).toContain(EXPLORER_TEXT.unseen);
    expect(row.textContent).toContain(EXPLORER_TEXT.noYear);
    expect(document.body.textContent).toContain(TEXT.absenceIsNotOpportunity);
  });

  it("shouldFilterUnseenPairsAndHideTheAbsenceSentenceOnlyWhenListingSeenPairs", async () => {
    const { user } = await open();
    await user.selectOptions(screen.getByLabelText("Par"), "unseen");
    expect(symbols()).toEqual(["A01B", "A01C", "H04L"]);
    await user.selectOptions(screen.getByLabelText("Par"), "seen");
    expect(symbols()).toEqual(["G06F"]);
    expect(document.body.textContent).not.toContain(TEXT.absenceIsNotOpportunity);
  });

  it("shouldFilterBySectionAndSortByDocumentsWithBothWhenAsked", async () => {
    const { user } = await open();
    await user.selectOptions(screen.getByLabelText("Sección de la otra subclase"), "A");
    expect(symbols()).toEqual(["A01B", "A01C"]);
    await user.selectOptions(screen.getByLabelText("Sección de la otra subclase"), "all");
    await user.selectOptions(screen.getByLabelText("Ordenar por"), "both");
    expect(symbols()[0]).toBe("G06F");
  });

  it("shouldOpenAPairWithItsCountsByYearAndMoveFocusToItWhenAskedFromTheKeyboard", async () => {
    const { user } = await open("A01B");
    await user.click(screen.getByRole("button", { name: "Ver el par A01B y A01C" }));
    const detail = screen.getByRole("region", { name: "Par A01B y A01C" });
    expect(detail).toBe(document.activeElement);
    expect(within(detail).getByRole("row", { name: /2003 13/ })).toBeTruthy();
  });

  it("shouldStateThatAnUnseenPairHasNoYearWhenOpeningIt", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Ver el par G06N y H04L" }));
    const detail = screen.getByRole("region", { name: "Par G06N y H04L" });
    expect(detail.textContent).toContain(`Par ${EXPLORER_TEXT.unseen}`);
    expect(detail.querySelector("table")).toBeNull();
  });

  it("shouldSwitchOriginAndDropSubclassesThatAreNotActiveThereWhenChangingIt", async () => {
    const { user } = await open("H04L");
    await user.selectOptions(screen.getByLabelText("Origen"), "2006");
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("shouldSayNothingMatchesAndRepeatTheUniverseRuleWhenTheSearchFindsNoActiveSubclass", async () => {
    await open("ZZZ");
    expect(document.body.textContent).toContain(EXPLORER_TEXT.universe);
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("shouldNeverUseFormulationsThatPresentAbsencesAsOpportunitiesWhenRendered", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Ver el par G06N y H04L" }));
    for (const pattern of FORBIDDEN) expect(document.body.textContent, String(pattern)).not.toMatch(pattern);
  });

  it("shouldReportAnErrorAndRetryOnTheNextLoadWhenTheFileCannotBeFetched", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 404, json: async () => ({}) })));
    render(<SubclassExplorerSection />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
