import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchScientificResults, ScientificResultsFetchError } from '../../src/infrastructure/scientificResultsHttpClient';
import { ScientificResultsValidationError } from '../../src/domain/scientificResults';

describe('ScientificResultsHttpClient (Infrastructure)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const validPayload = {
    schema_version: '0.1.0',
    generated_at: '2026-09-09T11:26:54.982691Z',
    executions: [
      {
        execution_id: 'exec-0001',
        track: 'discovery',
        domain: 'solid_state_battery',
        query: 'solid electrolyte',
        created_at: '2026-09-09T11:26:54.982691Z',
        dataset_id: null,
        dataset_version: null,
        engine_commit: null,
        policy_id: null,
        policy_version: null,
        policy_sha256: null,
        source_provenance: [],
      },
    ],
    landscapes: [],
    candidates: [],
    verifications: [],
    matches: [],
  };

  it('successfully fetches and parses a valid scientific results document', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validPayload,
    } as Response);

    const result = await fetchScientificResults('./scientific_results.json');
    expect(result.schema_version).toBe('0.1.0');
    expect(result.executions[0].track).toBe('discovery');
  });

  it('throws ScientificResultsFetchError on HTTP non-200 response', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    } as Response);

    await expect(fetchScientificResults('./scientific_results.json')).rejects.toThrow(
      ScientificResultsFetchError
    );
    await expect(fetchScientificResults('./scientific_results.json')).rejects.toThrow(
      /HTTP 404: Not Found/
    );
  });

  it('throws ScientificResultsFetchError on network/connection failure', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network disconnected'));

    await expect(fetchScientificResults('./scientific_results.json')).rejects.toThrow(
      ScientificResultsFetchError
    );
    await expect(fetchScientificResults('./scientific_results.json')).rejects.toThrow(
      /Failed to fetch scientific results contract: Network disconnected/
    );
  });

  it('throws ScientificResultsFetchError when response is invalid JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('Unexpected token < in JSON at position 0');
      },
    } as unknown as Response);

    await expect(fetchScientificResults('./scientific_results.json')).rejects.toThrow(
      ScientificResultsFetchError
    );
  });

  it('throws ScientificResultsValidationError when payload violates the contract, not an empty result', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ generated_at: '2026-09-09T11:26:54.982691Z' }), // missing schema_version
    } as unknown as Response);

    await expect(fetchScientificResults('./scientific_results.json')).rejects.toThrow(
      ScientificResultsValidationError
    );
  });

  it('throws ScientificResultsValidationError when discovery/verification tracks are mixed', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ...validPayload,
        executions: [{ ...validPayload.executions[0], track: 'verification', execution_id: 'exec-0001' }],
        landscapes: [{ execution_id: 'exec-0001', query: 'q', clusters: [], disclaimer: 'd' }],
      }),
    } as unknown as Response);

    await expect(fetchScientificResults('./scientific_results.json')).rejects.toThrow(
      /discovery and verification cannot be mixed/
    );
  });
});
