import type { DemandExamplesResponse, MatchesResponse } from "../domain/operational";

export class ApiError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const isContract = typeof body?.code === "string" && typeof body?.message === "string";
    throw new ApiError(isContract ? body.code : "UNKNOWN_ERROR", isContract ? body.message : `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function getDemandExamples(): Promise<DemandExamplesResponse> {
  return getJson<DemandExamplesResponse>(`/api/demand-examples`);
}

export function getMatches(demandId: string, limit = 5): Promise<MatchesResponse> {
  const params = new URLSearchParams({ demand_id: demandId, limit: String(limit) });
  return getJson<MatchesResponse>(`/api/matches?${params}`);
}
