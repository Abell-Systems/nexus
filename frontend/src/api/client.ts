// Thin fetch wrapper for the backend. getLandscape hits the deterministic
// /api/landscape endpoint (research + clustering, no Gemini call); analyzeCluster
// runs the full Gemini-backed agent graph via POST /api/analyze.

import type {
  AdversarialVerdict,
  InventionCandidate,
  JobStatusResponse,
  JobSummary,
  PatentCluster,
  PatentRecord,
  PipelineStage,
  ScoreCard,
} from "../types/patent";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const API_BASE = API_BASE_URL;

async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Request failed (${response.status}): ${body.slice(0, 300)}`);
  }
  return response.json();
}

export interface LandscapeResponse {
  query: string;
  domain: string;
  patents: PatentRecord[];
  clusters: PatentCluster[];
}

export async function getLandscape(
  query: string,
  domain: string,
  maxResults = 20,
  signal?: AbortSignal,
): Promise<LandscapeResponse> {
  const params = new URLSearchParams({ query, domain, max_results: String(maxResults) });
  return (await requestJson(`${API_BASE_URL}/api/landscape?${params}`, { signal })) as LandscapeResponse;
}

export interface AnalyzeResult {
  candidates: InventionCandidate[];
  verdicts: AdversarialVerdict[];
  scorecards: ScoreCard[];
}

export type AnalyzeStatus = JobStatusResponse;

// POST kicks off the agent graph in the background and returns a job id;
// poll getAnalyzeStatus until status is "done" or "error".
export async function startAnalyze(
  domain: string,
  query?: string,
): Promise<{ job_id: string; status: string; stage: PipelineStage }> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain, query: query || "solid electrolyte interphase" }),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as { detail?: string };
    throw new Error(err.detail || "Failed to start analysis");
  }
  return res.json() as Promise<{ job_id: string; status: string; stage: PipelineStage }>;
}

export async function getAnalyzeStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/api/analyze/${jobId}`);
  if (!res.ok) {
    throw new Error(`Failed to check analysis status: ${res.statusText}`);
  }
  return res.json() as Promise<JobStatusResponse>;
}

// Lists past/in-progress analyze jobs from this process's in-memory job
// store. Opening one still goes through getAnalyzeStatus, which returns the
// already-computed result -- no new Gemini/BigQuery calls.
export async function listAnalyzeJobs(): Promise<JobSummary[]> {
  const res = await fetch(`${API_BASE}/api/analyze`);
  if (!res.ok) {
    throw new Error(`Failed to list past analyses: ${res.statusText}`);
  }
  const data = (await res.json()) as { jobs: JobSummary[] };
  return data.jobs;
}

