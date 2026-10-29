import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { TopicMapResult } from "../../src/main/domain/topicMap";
import { TopicMapPage } from "../../src/main/components/TopicMap/TopicMapPage";

const years = [...Array.from({ length: 10 }, (_, i) => 2000 + i), ...Array.from({ length: 15 }, (_, i) => 2011 + i)];
const names = (n: number, p: string) => Array.from({ length: n }, (_, i) => `${p} ${i + 1}`);

function fixture(over: Partial<TopicMapResult> = {}): TopicMapResult {
  return {
    schema: "topic-map/1",
    configuration: { id: "x", parameters: { schema: "p", definition_id: "d", applicant_rules_id: "a", min_observed: 30, min_expected: 30, max_ratio: 0.8, unit: "u" } },
    corpus: { source_id: "s", files: {} },
    names_reviewed: true,
    unreviewed: [],
    topic: { key: "baterias", name: "Baterías", noun: "baterías", joined: "junto a baterías" },
    total_documents: 1000,
    corpus_documents: 5000,
    years,
    trend: years.map((year) => ({ year, documents: year === 2024 || year === 2025 ? 100 : 10, share: 2, ep_documents: 5 })),
    ep_share: 0.5,
    top_applicant_recent: { name: "Acme", by_year: years.map((y) => (y >= 2024 ? 60 : 1)) },
    subareas: [
      ...names(6, "Parte").map((name, i) => ({ key: `k${i}`, name, description: `Descripción ${i}`, documents: 100 - i, series: [] })),
      { key: "vacia", name: "Parte vacía", description: "Sin nada", documents: 0, series: [] },
    ],
    neighbours: names(7, "Vecino").map((name) => ({ subclass: "H01M", name, documents: 50 })),
    rare: [
      { subclass: "A61K", name: "Alfa", observed: 1, expected: 40.4, ratio: 0.9 },
      { subclass: "B01D", name: "Beta", observed: 35, expected: 50, ratio: 0.7 },
      { subclass: "C02F", name: "Gamma", observed: 31, expected: 100, ratio: 0.31 },
    ],
    applicants: names(6, "Empresa").map((name, i) => ({ name, documents: 600 - i * 10, originals: [`${name} S.A.`] })),
    ...over,
  };
}

const go = (hash: string) => act(() => { window.location.hash = hash; });
const IPC = /\b[A-HY]\d{2}[A-Z]\b/;
const VIEW_HASHES = ["#/baterias", "#/baterias/evolucion", "#/baterias/tema", "#/baterias/quien", "#/baterias/pistas"];

beforeEach(() => { window.location.hash = ""; });
afterEach(() => { window.location.hash = ""; });

describe("the topic map page", () => {
  it("shouldShowNoTenemosEseTemaWhenTheSearchMatchesNothing", async () => {
    const { container } = render(<TopicMapPage load={async () => fixture()} />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "zzz" } });
    expect(screen.getByText("No tenemos ese tema todavía.")).toBeTruthy();
    expect(screen.queryAllByRole("link").filter((a) => a.getAttribute("href")?.startsWith("#/b"))).toHaveLength(0);
    expect(container.querySelector("main")?.textContent).toBe("¿Qué tecnología te interesa?Buscar un tema" + "No tenemos ese tema todavía.");
  });

  it("shouldShowTheEntryViewWhenTheTopicIsUnknown", async () => {
    window.location.hash = "#/nada";
    render(<TopicMapPage load={async () => fixture()} />);
    expect(screen.getByRole("heading", { name: "¿Qué tecnología te interesa?" })).toBeTruthy();
  });

  it("shouldShowFourButtonsOnTheSummary", async () => {
    window.location.hash = "#/baterias";
    render(<TopicMapPage load={async () => fixture()} />);
    for (const label of ["¿Cómo evoluciona?", "¿De qué trata?", "¿Quién está?", "Pistas sin explorar"]) {
      expect(await screen.findByRole("link", { name: label })).toBeTruthy();
    }
  });

  it("shouldFollowTheHashWhenTheUserNavigates", async () => {
    window.location.hash = "#/baterias";
    render(<TopicMapPage load={async () => fixture()} />);
    await screen.findByRole("link", { name: "¿Quién está?" });
    await go("#/baterias/quien");
    expect(await screen.findByText(/Empresa 1 figura como solicitante en el 60 % de los documentos\. Después, Empresa 2 y Empresa 3\./)).toBeTruthy();
    expect(screen.getByText("Baterías").closest("nav")).toBeTruthy();
  });

  it("shouldFoldListsBeyondFiveWithAVerNMasControl", async () => {
    window.location.hash = "#/baterias/tema";
    const { container } = render(<TopicMapPage load={async () => fixture()} />);
    expect(await screen.findAllByText("Ver 2 más")).toHaveLength(2); // 7 subareas and 7 neighbours
    expect(screen.getAllByText("Ver 2 más")[0].closest("details")?.querySelectorAll("li")).toHaveLength(2);
    expect(container.querySelectorAll("details")).toHaveLength(2);
    expect(screen.getByText(/Aparecen sobre todo junto a Vecino 1, Vecino 2 y Vecino 3\./)).toBeTruthy();
    expect(screen.getByText(/Lo más habitual es Parte 1 \(10 % de los documentos\)\. Un mismo documento puede estar en más de una\./)).toBeTruthy();
  });

  it("shouldRenderASubareaWithZeroDocuments", async () => {
    window.location.hash = "#/baterias/tema";
    render(<TopicMapPage load={async () => fixture()} />);
    const row = (await screen.findByText("Parte vacía")).closest("li")!;
    expect(within(row).getByText("0 documentos")).toBeTruthy();
  });

  it("shouldDrawTheApplicantPartAndTheGapWhenOneApplicantDominates", async () => {
    window.location.hash = "#/baterias/evolucion";
    const { container } = render(<TopicMapPage load={async () => fixture()} />);
    const svg = await screen.findByRole("img");
    expect(svg.getAttribute("aria-label")).toContain("Acme figura como solicitante");
    expect(screen.getByText("Solo los de Acme")).toBeTruthy();
    expect(container.querySelector("svg title")).toBeTruthy();
    expect(Array.from(container.querySelectorAll("svg title")).some((t) => t.textContent === "2010: sin datos")).toBe(true);
    expect(container.textContent).toContain("año de publicación en España");
  });

  it("shouldKeepTheCluesInTheGivenOrderWithoutScoresWhenThereAreRareRows", async () => {
    window.location.hash = "#/baterias/pistas";
    const { container } = render(<TopicMapPage load={async () => fixture()} />);
    await screen.findByText(/Son pistas para investigar, no oportunidades/);
    const rows = Array.from(container.querySelectorAll("li strong")).map((s) => s.textContent);
    expect(rows).toEqual(["Alfa", "Beta", "Gamma"]); // alphabetical as given; by ratio it would be Gamma, Beta, Alfa
    expect(container.textContent).toContain("Aparece 1 vez junto a baterías; por su tamaño cabría esperar unas 40.");
    expect(container.textContent).toContain("Aparece 35 veces junto a baterías; por su tamaño cabría esperar unas 50.");
    expect(container.textContent).toContain("El criterio es provisional y no está validado.");
  });

  it("shouldTellThereAreNoRowsWhenNothingQualifies", async () => {
    window.location.hash = "#/baterias/pistas";
    const { container } = render(<TopicMapPage load={async () => fixture({ rare: [] })} />);
    expect(await screen.findByText("Ningún tema vecino cumple el criterio provisional todavía.")).toBeTruthy();
    expect(container.querySelector("svg")).toBeNull();
    expect(container.querySelector("li")).toBeNull();
  });

  it("shouldNotShowAnyIpcCodeInVisibleText", async () => {
    // a plain name that is a code would be a data error; here the codes live only in the subclass fields
    for (const hash of VIEW_HASHES) {
      window.location.hash = hash;
      const { container, unmount } = render(<TopicMapPage load={async () => fixture()} />);
      await screen.findByRole("heading", { level: 1 });
      await waitFor(() => expect(container.textContent).not.toContain("Cargando"));
      // test every text node on its own: adjacent nodes glued together would hide a code from the word boundary
      const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) expect(n.textContent).not.toMatch(IPC);
      unmount();
    }
    // control: the matcher does detect a leaked code
    expect("Parte H01M").toMatch(IPC);
  });

  it("shouldShowDatosNoDisponiblesWhenTheLoadFails", async () => {
    window.location.hash = "#/baterias/quien";
    const { container } = render(<TopicMapPage load={() => Promise.reject(new Error("hash mismatch"))} />);
    expect(await screen.findByText("Datos no disponibles")).toBeTruthy();
    expect(container.querySelector("main")?.textContent).toBe("Datos no disponibles");
    expect(screen.getByRole("button", { name: "Cómo leer esto" })).toBeTruthy();
    expect(screen.getByText("Baterías")).toBeTruthy();
  });

  it("shouldShowTheUnreviewedMarkOnEveryViewWhenTheResultSaysSo", async () => {
    for (const hash of VIEW_HASHES) {
      window.location.hash = hash;
      const { unmount } = render(<TopicMapPage load={async () => fixture({ names_reviewed: false })} />);
      expect(await screen.findByText("Nombres sin revisar")).toBeTruthy();
      unmount();
    }
  });

  it("shouldNotShowTheMarkWhenAllNamesAreReviewed", async () => {
    window.location.hash = "#/baterias/quien";
    render(<TopicMapPage load={async () => fixture()} />);
    await screen.findByText(/figura como solicitante/);
    expect(screen.queryByText("Nombres sin revisar")).toBeNull();
  });

  it("shouldOpenAndCloseTheHelpDialogWithTheKeyboard", async () => {
    window.location.hash = "#/baterias";
    render(<TopicMapPage load={async () => fixture()} />);
    await screen.findByRole("link", { name: "¿Quién está?" });
    const button = screen.getByRole("button", { name: "Cómo leer esto" });
    button.focus();
    fireEvent.click(button); // Enter and Space on a native button end in a click
    const dialog = screen.getByRole("dialog", { name: "Cómo leer esto" });
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(document.activeElement!, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(button);
    fireEvent.click(button);
    fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(button);
  });
});
