import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CausalChain } from "../../src/main/components/UserZero/CausalChain";

describe("CausalChain Component", () => {
  const sampleCandidate = {
    candidate_id: "cand-1",
    cluster_id: "cl-1",
    title: "Solid Electrolyte",
    description: "Electrolyte with ceramic coating",
    claimed_novelty: "Novel coating",
  };

  const sampleCluster = {
    cluster_id: "cl-1",
    label: "Ceramic Solid Separators",
    representative_patents: ["ES-1234567-A1"],
    patent_count: 12,
    white_space_score: 0.82,
    is_white_space: true,
  };

  const sampleVerdict = {
    candidate_id: "cand-1",
    verdict: "survives" as const,
    rationale: "Clear novelty verified against baseline.",
    cited_patents: ["ES-1234567-A1"],
  };

  const sampleScorecard = {
    candidate_id: "cand-1",
    novelty: 0.9,
    prior_art_risk: 0.1,
    market_traction: 0.85,
    overall_recommendation: 0.88,
    summary: "Recommended for commercial filing.",
    supporting_evidence: ["ES-1234567-A1 shows distinct binder matrix"],
  };

  it("renders causal nodes and allows step navigation", () => {
    render(
      <CausalChain
        cluster={sampleCluster}
        candidate={sampleCandidate}
        verdict={sampleVerdict}
        scorecard={sampleScorecard}
      />
    );

    expect(screen.getByText("Causal Chain Trace")).toBeDefined();
    expect(screen.getByText("OPPORTUNITY")).toBeDefined();

    // Step 2: Prior Art
    const priorArtNode = screen.getByText("PRIOR ART");
    fireEvent.click(priorArtNode);
    expect(screen.getByText("2. PRIOR ART")).toBeDefined();

    // Step 3: Prior-Art Challenge
    const challengeNode = screen.getByText("PRIOR-ART CHALLENGE");
    fireEvent.click(challengeNode);
    expect(screen.getByText("3. PRIOR-ART CHALLENGE")).toBeDefined();

    // Step 4: Revision
    const revisionNode = screen.getByText("REVISION");
    fireEvent.click(revisionNode);
    expect(screen.getByText("4. REVISION")).toBeDefined();

    // Step 5: Survival
    const survivalNode = screen.getByText("SURVIVAL");
    fireEvent.click(survivalNode);
    expect(screen.getByText("5. SURVIVAL")).toBeDefined();

    // Step 6: Evidence
    const evidenceNode = screen.getByText("EVIDENCE");
    fireEvent.click(evidenceNode);
    expect(screen.getByText("6. EVIDENCE")).toBeDefined();
  });

  it("toggles expand all steps view", () => {
    render(
      <CausalChain
        cluster={sampleCluster}
        candidate={sampleCandidate}
        verdict={sampleVerdict}
        scorecard={sampleScorecard}
      />
    );

    const expandBtn = screen.getByRole("button", { name: /expand all 6 steps/i });
    fireEvent.click(expandBtn);
    expect(screen.getByRole("button", { name: /show step by step/i })).toBeDefined();
  });
});
