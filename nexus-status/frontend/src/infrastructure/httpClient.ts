import { parseProjectStatus, type ProjectStatus } from '../domain/status';

export class ProjectStatusFetchError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ProjectStatusFetchError';
    this.status = status;
  }
}

/**
 * Fetches the canonical Project Status contract from a target endpoint (defaults to './project_status.json'),
 * parses the response body, and validates it against the Project Status Contract v1 domain model.
 *
 * Throws:
 *  - ProjectStatusFetchError: Network failure, HTTP status != 200, or invalid JSON syntax.
 *  - ContractValidationError: Schema version mismatch or contract invariant violation.
 */
export async function fetchProjectStatus(
  url: string = './project_status.json'
): Promise<ProjectStatus> {
  let response: Response;
  try {
    response = await fetch(url);
  } catch (err: unknown) {
    const detail = err instanceof Error ? err.message : String(err);
    throw new ProjectStatusFetchError(
      `Failed to fetch project status contract: ${detail}`
    );
  }

  if (!response.ok) {
    throw new ProjectStatusFetchError(
      `HTTP ${response.status}: ${response.statusText || 'Failed to load status contract'}`,
      response.status
    );
  }

  let rawJson: unknown;
  try {
    rawJson = await response.json();
  } catch (err: unknown) {
    const detail = err instanceof Error ? err.message : String(err);
    throw new ProjectStatusFetchError(
      `Failed to parse JSON response: ${detail}`,
      response.status
    );
  }

  return parseProjectStatus(rawJson);
}
