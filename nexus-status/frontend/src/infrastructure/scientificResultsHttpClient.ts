import { parseScientificResults, type ScientificResultsDocument } from '../domain/scientificResults';

export class ScientificResultsFetchError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ScientificResultsFetchError';
    this.status = status;
  }
}

/**
 * Fetches the canonical Scientific Results contract from a target endpoint (defaults
 * to './scientific_results.json'), parses the response body, and validates it against
 * the Scientific Results Contract v1 domain model (ADR 0025).
 *
 * `scientific_results.json` is a statically-published, git-tracked sibling artifact of
 * `project_status.json` — this fetches it as a plain static file, the same way
 * `fetchProjectStatus` does, introducing no new backend or API.
 *
 * Throws:
 *  - ScientificResultsFetchError: Network failure, HTTP status != 200, or invalid JSON syntax.
 *  - ScientificResultsValidationError: Contract invariant violation (missing/invalid
 *    fields, or a discovery/verification track mismatch).
 */
export async function fetchScientificResults(
  url: string = './scientific_results.json'
): Promise<ScientificResultsDocument> {
  let response: Response;
  try {
    response = await fetch(url);
  } catch (err: unknown) {
    const detail = err instanceof Error ? err.message : String(err);
    throw new ScientificResultsFetchError(
      `Failed to fetch scientific results contract: ${detail}`
    );
  }

  if (!response.ok) {
    throw new ScientificResultsFetchError(
      `HTTP ${response.status}: ${response.statusText || 'Failed to load scientific results contract'}`,
      response.status
    );
  }

  let rawJson: unknown;
  try {
    rawJson = await response.json();
  } catch (err: unknown) {
    const detail = err instanceof Error ? err.message : String(err);
    throw new ScientificResultsFetchError(
      `Failed to parse JSON response: ${detail}`,
      response.status
    );
  }

  return parseScientificResults(rawJson);
}
