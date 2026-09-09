import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchProjectStatus, ProjectStatusFetchError } from '../../src/infrastructure/httpClient';
import { ContractValidationError } from '../../src/domain/status';

describe('ProjectStatusHttpClient (Infrastructure)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const validPayload = {
    schema_version: '1.0.0',
    commit_sha: 'abc1234567',
    evaluated_at: '2026-09-09T10:00:00.000Z',
    overall_status: 'PASS',
    aggregation_rule: 'All required dimensions verified and passed.',
    summary: 'Repository status verified.',
    dimensions: {
      scientific_integrity: {
        status: 'PASS',
        requirement_level: 'required',
        evidence_source: 'docs/paper/results.json',
        evidence_available: true,
        checks: [
          { name: 'effect_size_test', status: 'PASS' },
        ],
      },
    },
  };

  it('successfully fetches and parses valid project status', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validPayload,
    } as Response);

    const result = await fetchProjectStatus('./project_status.json');
    expect(result.schema_version).toBe('1.0.0');
    expect(result.commit_sha).toBe('abc1234567');
    expect(result.overall_status).toBe('PASS');
    expect(result.dimensions.scientific_integrity.status).toBe('PASS');
  });

  it('throws ProjectStatusFetchError on HTTP non-200 response', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    } as Response);

    await expect(fetchProjectStatus('./project_status.json')).rejects.toThrow(
      ProjectStatusFetchError
    );
    await expect(fetchProjectStatus('./project_status.json')).rejects.toThrow(
      /HTTP 404: Not Found/
    );
  });

  it('throws ProjectStatusFetchError on network/connection failure', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network disconnected'));

    await expect(fetchProjectStatus('./project_status.json')).rejects.toThrow(
      ProjectStatusFetchError
    );
    await expect(fetchProjectStatus('./project_status.json')).rejects.toThrow(
      /Failed to fetch project status contract: Network disconnected/
    );
  });

  it('throws ProjectStatusFetchError when response is invalid JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('Unexpected token < in JSON at position 0');
      },
    } as unknown as Response);

    await expect(fetchProjectStatus('./project_status.json')).rejects.toThrow(
      ProjectStatusFetchError
    );
    await expect(fetchProjectStatus('./project_status.json')).rejects.toThrow(
      /Failed to parse JSON response/
    );
  });

  it('throws ContractValidationError when payload violates domain contract', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        schema_version: '999.0.0', // Unsupported version
        commit_sha: '123',
      }),
    } as unknown as Response);

    await expect(fetchProjectStatus('./project_status.json')).rejects.toThrow(
      ContractValidationError
    );
  });
});
