import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAnalyzeJob } from "../../src/main/application/useAnalyzeJob";
import * as client from "../../src/main/infrastructure/client";

describe("Frontend Application useAnalyzeJob Hook", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("initializes with default landing view", () => {
    const { result } = renderHook(() => useAnalyzeJob());
    expect(result.current.view).toBe("landing");
    expect(result.current.jobId).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("starts analysis successfully and transitions to executing", async () => {
    vi.spyOn(client, "startAnalyze").mockResolvedValueOnce({
      job_id: "test-job-42",
      status: "running",
      stage: "research",
    });

    const { result } = renderHook(() => useAnalyzeJob());

    await act(async () => {
      await result.current.startAnalysis("solid_state_battery", "electrolyte");
    });

    expect(result.current.view).toBe("executing");
    expect(result.current.jobId).toBe("test-job-42");
    expect(result.current.domain).toBe("solid_state_battery");
    expect(result.current.query).toBe("electrolyte");
  });

  it("handles startAnalysis failure by transitioning to error view", async () => {
    vi.spyOn(client, "startAnalyze").mockRejectedValueOnce(new Error("Network connection lost"));

    const { result } = renderHook(() => useAnalyzeJob());

    await act(async () => {
      await result.current.startAnalysis("solid_state_battery", "electrolyte");
    });

    expect(result.current.view).toBe("error");
    expect(result.current.errorMessage).toBe("Network connection lost");
  });

  it("handles polling reaching done state", async () => {
    vi.useFakeTimers();
    vi.spyOn(client, "startAnalyze").mockResolvedValueOnce({
      job_id: "test-job-poll",
      status: "running",
      stage: "research",
    });
    vi.spyOn(client, "getAnalyzeStatus").mockResolvedValue({
      job_id: "test-job-poll",
      status: "done",
      stage: "complete",
    });

    const { result } = renderHook(() => useAnalyzeJob());

    await act(async () => {
      await result.current.startAnalysis("battery", "anode");
    });

    await act(async () => {
      vi.advanceTimersByTime(2100);
    });

    expect(result.current.view).toBe("results");
    vi.useRealTimers();
  });

  it("handles polling reaching error state", async () => {
    vi.useFakeTimers();
    vi.spyOn(client, "startAnalyze").mockResolvedValueOnce({
      job_id: "test-job-err",
      status: "running",
      stage: "research",
    });
    vi.spyOn(client, "getAnalyzeStatus").mockResolvedValue({
      job_id: "test-job-err",
      status: "error",
      stage: "research",
      error: "Quota exceeded",
      error_type: "quota_exhausted",
    });

    const { result } = renderHook(() => useAnalyzeJob());

    await act(async () => {
      await result.current.startAnalysis("battery", "anode");
    });

    await act(async () => {
      vi.advanceTimersByTime(2100);
    });

    expect(result.current.view).toBe("error");
    expect(result.current.errorMessage).toBe("Quota exceeded");
    expect(result.current.errorType).toBe("quota_exhausted");
    vi.useRealTimers();
  });

  it("opens history view and resets error state", () => {
    const { result } = renderHook(() => useAnalyzeJob());

    act(() => {
      result.current.openHistory();
    });

    expect(result.current.view).toBe("history");
    expect(result.current.errorMessage).toBeNull();
  });

  it("resets state back to landing view", () => {
    const { result } = renderHook(() => useAnalyzeJob());

    act(() => {
      result.current.reset();
    });

    expect(result.current.view).toBe("landing");
    expect(result.current.jobId).toBeNull();
    expect(result.current.jobStatus).toBeNull();
  });

  it("retries previous analysis with existing domain", async () => {
    vi.spyOn(client, "startAnalyze").mockResolvedValue({
      job_id: "test-job-retry",
      status: "running",
      stage: "research",
    });

    const { result } = renderHook(() => useAnalyzeJob());

    await act(async () => {
      await result.current.startAnalysis("solid_state_battery", "electrolyte");
    });

    await act(async () => {
      result.current.retry();
    });

    expect(result.current.domain).toBe("solid_state_battery");
  });

  it("opens an existing job from history", async () => {
    vi.spyOn(client, "getAnalyzeStatus").mockResolvedValueOnce({
      job_id: "history-job-1",
      status: "done",
      domain: "solid_state_battery",
      query: "separator",
      stage: "complete",
    });

    const { result } = renderHook(() => useAnalyzeJob());

    await act(async () => {
      await result.current.openJob("history-job-1");
    });

    expect(result.current.jobId).toBe("history-job-1");
    expect(result.current.domain).toBe("solid_state_battery");
    expect(result.current.query).toBe("separator");
    expect(result.current.view).toBe("results");
  });

  it("handles openJob error gracefully", async () => {
    vi.spyOn(client, "getAnalyzeStatus").mockRejectedValueOnce(new Error("Job not found"));

    const { result } = renderHook(() => useAnalyzeJob());

    await act(async () => {
      await result.current.openJob("non-existent");
    });

    expect(result.current.view).toBe("error");
    expect(result.current.errorMessage).toBe("Job not found");
  });
});
