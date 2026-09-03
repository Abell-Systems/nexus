import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExecutionView } from "../../src/main/components/UserZero/ExecutionView";

describe("ExecutionView Component", () => {
  it("renders active domain and pipeline stage steps with progress metrics", () => {
    render(
      <ExecutionView
        domain="Solid-state electrolytes"
        stage="adversarial"
        progress={{
          patentsAnalyzed: 150,
          clustersFound: 4,
          candidatesGenerated: 6,
          candidatesRejected: 2,
          candidatesRevised: 1,
          candidatesSurvived: 3,
        }}
      />
    );
    expect(screen.getByText("Solid-state electrolytes")).toBeDefined();
    expect(screen.getByText("Research patent landscape")).toBeDefined();
    expect(screen.getByText("150 patents")).toBeDefined();
    expect(screen.getByText("4 opportunities")).toBeDefined();
    expect(screen.getByText("6 candidates")).toBeDefined();
    expect(screen.getByText("2 rejected / 1 revised / 3 survived")).toBeDefined();
  });

  it("renders live events when present", () => {
    render(
      <ExecutionView
        domain="Solid-state electrolytes"
        stage="inventing"
        events={[
          {
            type: "candidate_generated",
            timestamp: "2026-09-02T12:00:00Z",
            message: "Generated candidate alpha",
          },
        ]}
      />
    );
    expect(screen.getByText("Generated candidate alpha")).toBeDefined();
  });

  it("renders surviving and rejected candidate lists when available", () => {
    render(
      <ExecutionView
        domain="Solid-state electrolytes"
        stage="governor"
        candidates={[
          {
            candidate_id: "cand-1",
            cluster_id: "cl-1",
            title: "Novel Ceramic Electrolyte",
            description: "Description 1",
            claimed_novelty: "Novelty 1",
          },
          {
            candidate_id: "cand-2",
            cluster_id: "cl-1",
            title: "Polymer Composite",
            description: "Description 2",
            claimed_novelty: "Novelty 2",
          },
        ]}
        verdicts={[
          {
            candidate_id: "cand-1",
            verdict: "survives",
            rationale: "Clear novelty",
            cited_patents: [],
          },
          {
            candidate_id: "cand-2",
            verdict: "rejected",
            rationale: "Anticipated by prior art",
            cited_patents: ["ES-12345"],
          },
        ]}
      />
    );

    expect(screen.getByText(/Novel Ceramic Electrolyte/i)).toBeDefined();
    expect(screen.getByText(/Survived/i)).toBeDefined();
    expect(screen.getByText(/Rejected/i)).toBeDefined();
  });
});
