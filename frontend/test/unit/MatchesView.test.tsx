import { beforeEach, describe, it, expect } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MatchesView } from "../../src/main/components/Matches/MatchesView";
import { ApiError } from "../../src/main/infrastructure/operationalClient";
import type { DemandExamplesResponse, MatchesResponse } from "../../src/main/domain/operational";

const NOTICES = ["Aviso 1", "Aviso 2", "Aviso 3", "Aviso 4"];

const EXAMPLES: DemandExamplesResponse = {
  demands: [
    { demand_id: "D-1", title: "Lighter vehicles", description: "Seeking new materials", origin_country: "Spain", posted_date: null, source_url: "https://example.org/d1" },
    { demand_id: "D-2", title: "Water sensors", description: "Cheap sensing", origin_country: "Spain", posted_date: null, source_url: "" },
  ],
  notices: NOTICES,
};

function matches(assets: MatchesResponse["assets"]): MatchesResponse {
  return {
    demand: { demand_id: "D-1", title: "Lighter vehicles", description: "Seeking new materials", source_url: "https://example.org/d1" },
    assets,
    meta: { retrieval: "dense", eligible_count: assets.length, corpus_id: "C", corpus_parquet_sha256: "a", embedding_index_sha256: "b", notices: NOTICES },
  };
}

const ASSET = {
  rank: 1, publication_id: "ES-1000002-U", title: "Dispositivo ligero", ip_type: "utility_model", country_code: "ES",
  kind_code: "U", assignees: ["BETA SL"], inventors: ["ANA"], publication_date: "2020-02-01",
  abstract: "Un dispositivo ligero.", abstract_language: "es", cpc_codes: ["B60K1/00"],
  source_links: { google_patents: "https://patents.google.com/patent/ES1000002U", espacenet: "https://worldwide.espacenet.com/patent/search?q=pn%3DES1000002U" },
};

function api(result: MatchesResponse | Error) {
  return {
    getDemandExamples: () => Promise.resolve(EXAMPLES),
    getMatches: () => (result instanceof Error ? Promise.reject(result) : Promise.resolve(result)),
  };
}

describe("MatchesView", () => {
  beforeEach(() => window.history.replaceState(null, "", "/"));

  it("shouldShowExampleDemandsAndTheFourFixedNoticesWhenNoDemandIsSelected", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    expect(await screen.findByText("Lighter vehicles")).toBeDefined();
    NOTICES.forEach((n) => expect(screen.getByText(n)).toBeDefined());
  });

  it("shouldShowRankTitleTypeHolderAndSourceLinkWhenADemandIsChosen", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText("Dispositivo ligero")).toBeDefined();
    expect(screen.getByText("#1")).toBeDefined();
    expect(screen.getByText(/Modelo de utilidad/)).toBeDefined();
    expect(screen.getByText(/BETA SL/)).toBeDefined();
    const link = screen.getByText("Google Patents").closest("a");
    expect(link?.getAttribute("href")).toBe("https://patents.google.com/patent/ES1000002U");
  });

  it("shouldShowTheAssetsOwnCpcAndNoMatchSignalsBlockWhenResultsAreShown", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    await screen.findByText("Dispositivo ligero");
    expect(screen.getByText(/Datos del activo/)).toBeDefined();
    expect(screen.getByText(/B60K1\/00/)).toBeDefined();
    expect(screen.queryByText(/Señales de coincidencia/)).toBeNull();
  });

  it("shouldShowAnEmptyStateWhenNoEligibleAssetExists", async () => {
    render(<MatchesView api={api(matches([]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText(/No hay activos elegibles/)).toBeDefined();
  });

  it("shouldShowAnErrorMessageWhenTheRequestFails", async () => {
    render(<MatchesView api={api(new Error("boom"))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText(/No se pudieron cargar los resultados/)).toBeDefined();
  });

  it("shouldNotRenderAnyScoreOrPercentageWhenResultsAreShown", async () => {
    const { container } = render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    await screen.findByText("Dispositivo ligero");
    expect(container.textContent).not.toMatch(/\d\.\d{2,}|%|score|similitud:/i);
  });

  it("shouldShowTheChosenDemandDescriptionAndSourceLinkWhenResultsAreShown", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText("Seeking new materials")).toBeDefined();
    expect(screen.getByText("Ver demanda original").closest("a")?.getAttribute("href")).toBe("https://example.org/d1");
  });

  it("shouldOmitTheSourceLinkWhenTheDemandHasNoSourceUrl", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Water sensors"));
    await screen.findByText("Cheap sensing");
    expect(screen.queryByText("Ver demanda original")).toBeNull();
  });

  it("shouldStateHowManyEligibleAssetsAreShownWhenResultsAreShown", async () => {
    const response = matches([ASSET]);
    response.meta.eligible_count = 44195;
    render(<MatchesView api={api(response)} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText(/1 de 44\.195 activos elegibles/)).toBeDefined();
  });

  it("shouldOpenOnlyTheFirstAbstractWhenSeveralResultsAreShown", async () => {
    const second = { ...ASSET, rank: 2, publication_id: "ES-1000003-U", title: "Otro dispositivo" };
    render(<MatchesView api={api(matches([ASSET, second]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    await screen.findByText("Otro dispositivo");
    const open = Array.from(document.querySelectorAll("details")).map((d) => d.open);
    expect(open).toEqual([true, false]);
  });

  it("shouldLabelTheAbstractAsEnglishWhenItsLanguageIsEnglish", async () => {
    render(<MatchesView api={api(matches([{ ...ASSET, abstract_language: "en" }]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText(/Resumen en inglés/)).toBeDefined();
  });

  it("shouldAnnounceTheLoadingStateWhenResultsAreBeingFetched", async () => {
    const pending = { getDemandExamples: () => Promise.resolve(EXAMPLES), getMatches: () => new Promise<MatchesResponse>(() => {}) };
    render(<MatchesView api={pending} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect((await screen.findByRole("status")).textContent).toMatch(/Buscando activos/);
  });

  it("shouldShowTheServerMessageWhenTheRequestFailsWithAnApiError", async () => {
    render(<MatchesView api={api(new ApiError("DEMAND_NOT_FOUND", "La demanda 'D-1' no existe."))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText("La demanda 'D-1' no existe.")).toBeDefined();
  });

  it("shouldWriteTheChosenDemandInTheUrlWhenADemandIsChosen", async () => {
    window.history.replaceState(null, "", "/");
    render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    await screen.findByText("Dispositivo ligero");
    expect(window.location.search).toBe("?demanda=D-1");
  });

  it("shouldShowTheResultsOfTheDemandInTheUrlWhenThePageIsOpenedWithIt", async () => {
    window.history.replaceState(null, "", "/?demanda=D-1");
    render(<MatchesView api={api(matches([ASSET]))} />);
    expect(await screen.findByText("Dispositivo ligero")).toBeDefined();
  });

  it("shouldIgnoreTheDemandInTheUrlWhenItIsNotOneOfTheExamples", async () => {
    window.history.replaceState(null, "", "/?demanda=NOPE");
    render(<MatchesView api={api(matches([ASSET]))} />);
    await screen.findByText("Lighter vehicles");
    expect(screen.queryByText("Dispositivo ligero")).toBeNull();
    window.history.replaceState(null, "", "/");
  });
});
