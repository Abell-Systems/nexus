import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WhiteSpacePage } from "../../src/main/components/WhiteSpace/WhiteSpacePage";
import { TEXT } from "../../src/main/domain/whitespace";
import { whitespaceData } from "../../src/main/infrastructure/whitespaceData";

const FORBIDDEN = [/prometedor/i, /pr[oó]xima oportunidad/i, /descubre/i, /oportunidades? (tecnol[oó]gica|de innovaci[oó]n) (detectad|identificad|encontrad)/i, /candidatos? (prometedor|recomendad)/i];

describe("the white-space front page", () => {
  it("shouldStateTheAttributionTheAbsenceRuleAndTheUnavailableStatusWhenRendered", () => {
    const { container } = render(<WhiteSpacePage />);
    const text = container.textContent ?? "";
    expect(text).toContain(TEXT.attribution);
    expect(text).toContain(TEXT.noSponsorship);
    expect(text).toContain("no se ha observado co-clasificación en este corpus y periodo");
    expect(text).toContain("No demuestra que las áreas no se combinen ni que exista una oportunidad tecnológica");
    expect(text).not.toMatch(/la mayor[ií]a refleja/);
    expect(text).toContain(TEXT.status);
    expect(text).toContain(TEXT.notValidation);
    expect(text).toContain(TEXT.yUnknown);
  });

  it("shouldNeverUseFormulationsThatPresentAbsencesAsOpportunitiesWhenRendered", () => {
    const { container } = render(<WhiteSpacePage />);
    for (const pattern of FORBIDDEN) expect(container.textContent, String(pattern)).not.toMatch(pattern);
  });

  it("shouldExposeLandmarksOneMainHeadingAndWorkingAnchorsWhenRendered", () => {
    const { container } = render(<WhiteSpacePage />);
    expect(screen.getByRole("main")).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Secciones de la página" })).toBeTruthy();
    expect(screen.getByRole("contentinfo")).toBeTruthy();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    for (const link of within(screen.getByRole("navigation")).getAllByRole("link")) {
      const id = link.getAttribute("href")!.slice(1);
      expect(container.querySelector(`#${id}`), id).not.toBeNull();
    }
  });

  it("shouldGiveTheCoverageChartATitleADescriptionAndADataTableWhenRendered", () => {
    render(<WhiteSpacePage />);
    const chart = screen.getByRole("img", { name: /Publicaciones por año/ });
    expect(chart.querySelector("desc")?.textContent).toMatch(/En 2010 no hay ninguna publicación presente/);
    expect(screen.getByText("Tabla de datos de la cobertura")).toBeTruthy();
  });

  it("shouldDrawBothMapsOnOneColourScaleAndStateItWhenRendered", () => {
    render(<WhiteSpacePage />);
    expect(screen.getAllByRole("table", { name: /% de pares de subclases activas ya vistos juntos/ })).toHaveLength(2);
    expect(screen.getByText("común a ambos mapas")).toBeTruthy();
  });

  it("shouldShowTheVersionedFiguresAndTheirHashesWhenRendered", () => {
    const { container } = render(<WhiteSpacePage />);
    const text = container.textContent ?? "";
    expect(text).toContain(new Intl.NumberFormat("es-ES").format(whitespaceData.exposure.exposure.inventory_publications));
    for (const file of whitespaceData.provenance.files) expect(text).toContain(file.sha256);
    expect(text).toContain(whitespaceData.exposure.authority_file.sha256);
  });
});
