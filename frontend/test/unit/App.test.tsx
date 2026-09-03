import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "../../src/main/App";
import * as useAnalyzeHook from "../../src/main/application/useAnalyzeJob";

describe("App Root Component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders landing view by default", () => {
    render(<App />);
    expect(screen.getByText("Start your analysis")).toBeDefined();
  });

  it("renders error view when view state is error", () => {
    vi.spyOn(useAnalyzeHook, "useAnalyzeJob").mockReturnValue({
      view: "error",
      domain: "Battery tech",
      query: "solid",
      jobId: "job-1",
      jobStatus: null,
      errorMessage: "Analysis generation timed out",
      errorType: "quota",
      isLoading: false,
      startAnalysis: vi.fn(),
      reset: vi.fn(),
      retry: vi.fn(),
      openHistory: vi.fn(),
      openJob: vi.fn(),
    });

    render(<App />);
    expect(screen.getByText("Analysis generation timed out")).toBeDefined();
    expect(screen.getByRole("button", { name: /try again/i })).toBeDefined();
  });
});
