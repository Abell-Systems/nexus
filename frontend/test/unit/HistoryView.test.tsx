import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { HistoryView } from "../../src/main/components/UserZero/HistoryView";
import * as client from "../../src/main/infrastructure/client";

describe("HistoryView Component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loaded jobs list and triggers onOpenJob", async () => {
    vi.spyOn(client, "listAnalyzeJobs").mockResolvedValueOnce([
      {
        job_id: "past-job-1",
        domain: "Biodegradable polymers",
        query: "packaging film",
        status: "done",
        created_at: "2026-09-01T12:00:00Z",
      },
    ]);

    const onOpenJob = vi.fn();
    render(<HistoryView onOpenJob={onOpenJob} onBack={vi.fn()} />);

    expect(screen.getByText("Loading past analyses…")).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("Biodegradable polymers")).toBeDefined();
    });

    const openItem = screen.getByText("Biodegradable polymers");
    fireEvent.click(openItem);
    expect(onOpenJob).toHaveBeenCalledWith("past-job-1");
  });

  it("renders empty state when no jobs are present", async () => {
    vi.spyOn(client, "listAnalyzeJobs").mockResolvedValueOnce([]);
    render(<HistoryView onOpenJob={vi.fn()} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("No analyses yet. Run one from the landing page.")).toBeDefined();
    });
  });

  it("renders error message on load failure", async () => {
    vi.spyOn(client, "listAnalyzeJobs").mockRejectedValueOnce(new Error("Database offline"));
    render(<HistoryView onOpenJob={vi.fn()} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Database offline")).toBeDefined();
    });
  });
});
