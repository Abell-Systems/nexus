import type { DemandExamplesResponse, MatchesResponse } from "../domain/operational";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function getDemandExamples(): Promise<DemandExamplesResponse> {
  return getJson<DemandExamplesResponse>(`${API_BASE_URL}/api/demand-examples`);
}

export function getMatches(demandId: string, limit = 5): Promise<MatchesResponse> {
  const params = new URLSearchParams({ demand_id: demandId, limit: String(limit) });
  return getJson<MatchesResponse>(`${API_BASE_URL}/api/matches?${params}`);
}
