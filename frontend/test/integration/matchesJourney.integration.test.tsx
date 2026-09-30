import { describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

// Runs only against a live backend started with NEXUS_MVP_ENABLED=1 and the frozen artifacts:
//   NEXUS_E2E_BASE_URL=http://127.0.0.1:8080 npx vitest run test/integration
const BASE_URL = process.env.NEXUS_E2E_BASE_URL;

describe.skipIf(!BASE_URL)("matches journey over real HTTP (component in jsdom)", () => {
  it("shouldShowFiveAssetsWithTheirAbstractAndSourceWhenADemoDemandIsChosen", async () => {
    vi.stubEnv("VITE_API_BASE_URL", BASE_URL);
    vi.resetModules();
    const { MatchesView } = await import("../../src/main/components/Matches/MatchesView");
    render(<MatchesView />);

    fireEvent.click(await screen.findByText(/new available technologies for water quality measurement/));

    expect(await screen.findByText("Ver demanda original")).toBeDefined();
    const results = await screen.findByRole("region", { name: "Resultados" });
    expect(results.querySelectorAll("article")).toHaveLength(5);
    expect(results.querySelector("details")?.open).toBe(true);
    const source = results.querySelector("a[href^='https://patents.google.com/patent/']");
    expect(source?.getAttribute("target")).toBe("_blank");
    cleanup();
  });
});
