import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ResultsView } from "../../src/main/components/UserZero/ResultsView";
import type { JobStatusResponse } from "../../src/main/domain/patent";

describe("ResultsView Component", () => {
  const sampleResult: JobStatusResponse = {
    job_id: "job-100",
    status: "done",
    stage: "complete",
    domain: "Solid-state electrolytes",
    candidates: [
      {
        candidate_id: "cand-1",
        cluster_id: "cl-1",
        title: "Novel Composite Electrolyte",
        description: "A composite electrolyte featuring ceramic nanoparticles.",
        claimed_novelty: "Unique ceramic binder interface.",
      },
    ],
    clusters: [
      {
        cluster_id: "cl-1",
        label: "Solid state separators",
        representative_patents: ["ES-2849102-B2"],
        patent_count: 10,
        white_space_score: 0.8,
        is_white_space: true,
      },
    ],
    verdicts: [
      {
        candidate_id: "cand-1",
        verdict: "survives",
        rationale: "No anticipatory prior art found in snapshot.",
        cited_patents: ["ES-2849102-B2"],
      },
    ],
    scorecards: [
      {
        candidate_id: "cand-1",
        novelty: 0.85,
        prior_art_risk: 0.15,
        market_traction: 0.9,
        overall_recommendation: 0.88,
        summary: "Highly recommended novel candidate.",
        supporting_evidence: ["ES-2849102-B2 shows difference in binder"],
      },
    ],
  };

  it("renders candidate titles and surviving verdicts", () => {
    render(<ResultsView result={sampleResult} onReset={vi.fn()} />);
    expect(screen.getByText("Novel Composite Electrolyte")).toBeDefined();
    expect(screen.getByText(/Survived prior-art review/i)).toBeDefined();
    expect(screen.getByText("Highly recommended novel candidate.")).toBeDefined();
  });

  it("toggles details drilldown when button is clicked", () => {
    render(<ResultsView result={sampleResult} onReset={vi.fn()} />);
    const detailsButton = screen.getByRole("button", { name: /details/i });
    fireEvent.click(detailsButton);
    expect(screen.getByText("Hide details")).toBeDefined();
  });

  it("renders empty state when no candidates exist", () => {
    render(
      <ResultsView
        result={{
          job_id: "job-empty",
          status: "done",
          stage: "complete",
          candidates: [],
        }}
        onReset={vi.fn()}
      />
    );
    expect(screen.getByText("No candidate inventions survived the prior-art challenge for this query.")).toBeDefined();
  });
});

