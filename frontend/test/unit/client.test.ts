import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getLandscape,
  startAnalyze,
  getAnalyzeStatus,
  listAnalyzeJobs,
} from "../../src/main/infrastructure/client";

describe("Frontend Infrastructure Client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches landscape data successfully", async () => {
    const mockLandscape = {
      query: "solid electrolyte",
      domain: "solid_state_battery",
      patents: [{ publication_number: "ES-1" }],
      clusters: [{ id: "c1", title: "Cluster 1" }],
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockLandscape,
    } as Response);

    const result = await getLandscape("solid electrolyte", "solid_state_battery", 10);
    expect(result.domain).toBe("solid_state_battery");
    expect(result.patents).toHaveLength(1);
    expect(result.clusters).toHaveLength(1);
  });

  it("throws error when getLandscape fails with non-ok status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => "Internal Server Error",
    } as Response);

    await expect(getLandscape("query", "domain")).rejects.toThrow("Request failed (500)");
  });

  it("starts analysis job via POST", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "job-123", status: "running", stage: "research" }),
    } as Response);

    const result = await startAnalyze("solid_state_battery", "electrolyte");
    expect(result.job_id).toBe("job-123");
    expect(result.status).toBe("running");
  });

  it("throws error when startAnalyze fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "Invalid domain specified" }),
    } as Response);

    await expect(startAnalyze("invalid_domain")).rejects.toThrow("Invalid domain specified");
  });

  it("gets analyze status by job ID", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "job-123", status: "done", stage: "complete" }),
    } as Response);

    const result = await getAnalyzeStatus("job-123");
    expect(result.job_id).toBe("job-123");
    expect(result.status).toBe("done");
  });

  it("throws error when getAnalyzeStatus fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      statusText: "Not Found",
    } as Response);

    await expect(getAnalyzeStatus("non-existent")).rejects.toThrow("Failed to check analysis status: Not Found");
  });

  it("lists past analyze jobs", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        jobs: [
          {
            job_id: "job-1",
            domain: "battery",
            query: "anode",
            status: "done",
            created_at: "2026-09-01T00:00:00Z",
          },
        ],
      }),
    } as Response);

    const jobs = await listAnalyzeJobs();
    expect(jobs).toHaveLength(1);
    expect(jobs[0].job_id).toBe("job-1");
  });

  it("throws error when listAnalyzeJobs fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      statusText: "Server Error",
    } as Response);

    await expect(listAnalyzeJobs()).rejects.toThrow("Failed to list past analyses: Server Error");
  });
});
