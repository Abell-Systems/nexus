import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentActivityFeed } from "../../src/main/components/UserZero/AgentActivityFeed";

describe("AgentActivityFeed Component", () => {
  it("renders empty state when no events are provided", () => {
    render(<AgentActivityFeed events={[]} isLive={true} />);
    expect(screen.getByText("Waiting for the agent's first move…")).toBeDefined();
    expect(screen.getByText("LIVE")).toBeDefined();
  });

  it("renders empty state when isLive is false", () => {
    render(<AgentActivityFeed events={[]} isLive={false} />);
    expect(screen.getByText("No activity recorded for this run.")).toBeDefined();
  });

  it("renders list of agent telemetry events with various status icons", () => {
    render(
      <AgentActivityFeed
        events={[
          {
            type: "candidate_generated",
            timestamp: "2026-09-02T12:00:00Z",
            message: "Candidate Alpha synthesized",
          },
          {
            type: "candidate_challenged",
            timestamp: "2026-09-02T12:01:00Z",
            message: "Challenged Alpha with ES-2849102-B2",
          },
          {
            type: "candidate_rejected",
            timestamp: "2026-09-02T12:02:00Z",
            message: "Candidate Beta rejected",
          },
          {
            type: "candidate_revised",
            timestamp: "2026-09-02T12:03:00Z",
            message: "Candidate Gamma claims revised",
          },
          {
            type: "candidate_survived",
            timestamp: "2026-09-02T12:04:00Z",
            message: "Candidate Alpha survived",
          },
          {
            type: "unknown_event_type",
            timestamp: "2026-09-02T12:05:00Z",
            message: "Generic telemetry info",
          },
        ]}
        isLive={true}
      />
    );

    expect(screen.getByText("Candidate Alpha synthesized")).toBeDefined();
    expect(screen.getByText("Challenged Alpha with ES-2849102-B2")).toBeDefined();
    expect(screen.getByText("Candidate Beta rejected")).toBeDefined();
    expect(screen.getByText("Candidate Gamma claims revised")).toBeDefined();
    expect(screen.getByText("Candidate Alpha survived")).toBeDefined();
    expect(screen.getByText("Generic telemetry info")).toBeDefined();
  });
});
