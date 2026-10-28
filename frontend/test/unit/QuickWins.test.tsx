import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MatchesPage } from "../../src/main/components/Matches/MatchesPage";
import { MatchesView } from "../../src/main/components/Matches/MatchesView";
import { WhiteSpacePage } from "../../src/main/components/WhiteSpace/WhiteSpacePage";
import { SKIP_TEXT } from "../../src/main/domain/whitespace";
import type { DemandExamplesResponse } from "../../src/main/domain/operational";

const css = (name: string) => readFileSync(join(__dirname, "../../src/main", name), "utf-8");

describe("skip link", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {}))));

  it.each([
    ["the front page", WhiteSpacePage],
    ["the matcher", MatchesPage],
  ])("shouldBeTheFirstFocusableElementAndPointToAFocusableMainWhenOn %s", (_name, Page) => {
    const { container } = render(<Page />);
    const first = container.querySelector<HTMLElement>("a[href], button, input, select, summary, [tabindex]");
    expect(first?.textContent).toBe(SKIP_TEXT);
    expect(first?.getAttribute("href")).toBe("#contenido");
    const main = container.querySelector("main");
    expect(main?.id).toBe("contenido");
    expect(main?.getAttribute("tabindex")).toBe("-1"); // focusable by script so that following the link moves the focus
    main!.focus();
    expect(document.activeElement).toBe(main);
  });
});

describe("retry in the matcher", () => {
  const EXAMPLES: DemandExamplesResponse = {
    demands: [{ demand_id: "D-1", title: "Lighter vehicles", description: "d", origin_country: "Spain", posted_date: null, source_url: "" }],
    notices: ["Aviso"],
  };
  beforeEach(() => window.history.replaceState(null, "", "/"));

  it("shouldLoadTheDemandsAgainWhenRetryIsPressedAfterTheyFailedToLoad", async () => {
    const getDemandExamples = vi.fn().mockRejectedValueOnce(new Error("down")).mockResolvedValue(EXAMPLES);
    render(<MatchesView api={{ getDemandExamples, getMatches: vi.fn() }} />);
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudieron cargar las demandas de ejemplo.");
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Lighter vehicles")).toBeDefined();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(getDemandExamples).toHaveBeenCalledTimes(2);
  });

  it("shouldAskForTheSameDemandAgainWhenRetryIsPressedAfterTheResultsFailedToLoad", async () => {
    const getMatches = vi.fn().mockRejectedValueOnce(new Error("down")).mockResolvedValue({ demand: EXAMPLES.demands[0], assets: [], meta: { retrieval: "dense", eligible_count: 0, corpus_id: "C", corpus_parquet_sha256: "a", embedding_index_sha256: "b", notices: [] } });
    render(<MatchesView api={{ getDemandExamples: () => Promise.resolve(EXAMPLES), getMatches }} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudieron cargar los resultados.");
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText(/No hay activos elegibles/)).toBeDefined();
    expect(getMatches).toHaveBeenCalledTimes(2);
    expect(getMatches).toHaveBeenLastCalledWith("D-1");
  });
});

describe("print style", () => {
  it("shouldHideOnlyTheNavigationAndTheEntryFormInTheModuleWhenPrinting", () => {
    const block = /@media print\s*{([\s\S]*?)\n}/.exec(css("components/WhiteSpace/WhiteSpacePage.module.css"))?.[1] ?? "";
    expect(block).not.toBe("");
    const hidden = [...block.matchAll(/([^{}]+){[^}]*display:\s*none/g)].map((m) => m[1].replace(/\/\*[\s\S]*?\*\//g, "").trim());
    expect(hidden).toEqual([".nav, .entry form"]);
  });
});

describe("focus indicator", () => {
  it("shouldNeverRemoveTheFocusOutlineInAnyStylesheetBecauseTheSkipLinkTargetNeedsItToBeFoundWhenFocused", () => {
    for (const name of ["index.css", "components/WhiteSpace/WhiteSpacePage.module.css", "components/Matches/MatchesView.module.css", "components/shared/BrandHeader.module.css"]) {
      expect(css(name), name).not.toMatch(/outline:\s*(none|0)\b/);
    }
  });

  it("shouldGiveEveryControlBothDimensionsOfTheMinimumTargetSize", () => {
    expect(css("index.css")).toContain("button, select, input, summary { min-height: 24px; min-width: 24px; }");
  });
});
